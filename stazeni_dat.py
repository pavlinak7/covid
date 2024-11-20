import requests
import logging
import configparser
from pymongo import MongoClient
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from pymongo.errors import BulkWriteError
from datetime import datetime, timedelta


#struktura logů
def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

def load_config(file_path):
    config = configparser.ConfigParser()
    config.read(file_path)
    return config

# Retry strategy for requests
def setup_session(config):
    session = requests.Session()
    retry = Retry(
        total=int(config['retry']['total']),
        backoff_factor=float(config['retry']['backoff_factor']),
        status_forcelist=[int(code) for code in config['retry']['status_forcelist'].split(',')]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


# Function to fetch all paginated data from a specific schema with progress bar
def fetch_all_data(schema, config, session, logger, some_date=None, update_date=None, end_date=None, max_consecutive_failures=10):
    all_data = []  # To store all documents
    page = 1  # Start from page 1
    consecutive_failures = 0  # Track consecutive fetch failures

    endpoint = config['schemas'][schema]  # Get the schema endpoint from config
    schema_name = endpoint  # Use this as the schema name in logs
    items_per_page = config['schemas'].getint(f'{schema}.itemsPerPage', 1000)
    timeout = config['api'].getint('timeout', 10)  # Get timeout from config, default to 10

    with tqdm(desc=f"Fetching {schema_name}", unit="page") as pbar:  # Add progress bar here
        while True:
            params = {
                "apiToken": config['api']['api_token'],
                "itemsPerPage": items_per_page,
                "page": page
            }
            if some_date:
                params["datum[before]"] = some_date
            if update_date:
                params["datum[strictly_after]"] = update_date
            if end_date:
                params["datum[strictly_before]"] = end_date

            url = f"{config['api']['base_url']}{endpoint}"

            try:
                response = session.get(url, params=params, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                if not data['hydra:member']:
                    break  # If no more data, break the loop

                all_data.extend(data['hydra:member'])  # Append the fetched data to all_data
                pbar.update(1)  # Update the progress bar for each page fetched

                page += 1  # Move to the next page
                consecutive_failures = 0  # Reset failure count on success

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching {schema_name} (page {page}): {e}")
                logger.error(f"Response content: {response.content if response else 'No response'}")
                consecutive_failures += 1

                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"Max consecutive failures reached for {schema_name}. Stopping fetch.")
                    break

    return all_data


# Function to save data to MongoDB in batches
def save_to_mongo(schema_name, data, db, logger, batch_size=1000):
    if data:
        collection = db[schema_name]  # Use the actual schema name for the MongoDB collection
        try:
            # Insert data in batches
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                collection.insert_many(batch)
        except BulkWriteError as bwe:
            logger.error(f"BulkWriteError occurred while saving data for {schema_name}: {bwe.details}")
        except Exception as e:
            logger.error(f"Failed to save data to MongoDB for {schema_name}: {e}")
    else:
        logger.info(f"No data to save for {schema_name}")


# Main function to loop through each schema and save the data
def save_all_schemas(config, db, session, logger, some_date=None, update_date=None, end_date=None):
    consecutive_no_data_schemas = 0
    max_no_data_schemas = int(config['general']['max_no_data_schemas'])

    for schema in config['schemas']:
        schema_name = config['schemas'][schema]  # Get the actual schema name from the config
        logger.info(f"Fetching data for {schema_name}...")  # Log with actual schema name
        data = fetch_all_data(schema, config, session, logger, some_date=some_date, update_date=update_date, end_date=end_date)

        if data:
            save_to_mongo(schema_name, data, db, logger)  # Pass schema_name here instead of schema
            consecutive_no_data_schemas = 0  # Reset on successful fetch
        else:
            logger.info(f"Skipping {schema_name} due to fetch error or no data.")  # Use actual schema name in logs
            consecutive_no_data_schemas += 1

            if consecutive_no_data_schemas >= max_no_data_schemas:
                logger.error("Max consecutive schemas with no data reached. Exiting.")
                break

