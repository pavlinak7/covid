import pymongo
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import psutil

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import geopandas as gpd
import json
from shapely.geometry import Polygon
import os



#############################################################################################
####################### Načtení kolekcí #####################################################
#############################################################################################

def load_collections_to_dfs(mongo_uri: str, db_name: str, fields_to_include: dict, batch_size: int = 1000,
                            max_workers: int = 4):

    client = pymongo.MongoClient(mongo_uri)
    db = client[db_name]
    collections = db.list_collection_names()  # List all collections in the database

    def check_memory(): # checking memory usage
        mem = psutil.virtual_memory()
        if mem.percent > 80:
            print("Memory usage is high, pausing execution...")
            while mem.percent > 80:
                mem = psutil.virtual_memory()

    # Function to load a collection in batches with specific fields
    def load_collection(collection):
        print(f"Loading collection {collection} in batches...")
        batches = []  # Collect all batch DataFrames in a list
        num_documents = db[collection].count_documents({})

        # Get fields to include for the current collection
        fields = fields_to_include.get(collection, [])
        # Create projection dictionary for MongoDB query
        projection = {field: 1 for field in fields}
        projection['_id'] = 0  # Exclude '_id' field by default

        for i in range(0, num_documents, batch_size):
            # Check memory usage before processing the next batch
            check_memory()

            # Load batch with only necessary fields
            batch_data = list(db[collection].find({}, projection).skip(i).limit(batch_size))
            batch_df = pd.DataFrame(batch_data)
            batches.append(batch_df)

        # Concatenate all batches at once
        return pd.concat(batches, ignore_index=True)

    # Using ThreadPoolExecutor to load collections in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(tqdm(executor.map(load_collection, collections), total=len(collections)))

    dfs = dict(zip(collections, results))

    return dfs

#############################################################################################
####################### obrázky #############################################################
#############################################################################################

def format_plot(ax): #společné řádky grafů
    # Hide unnecessary spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # Restore the y-axis label and add barely visible horizontal lines
    ax.yaxis.set_visible(True)
    ax.yaxis.set_ticks_position('none')  # Removes y-axis ticks but keeps the labels
    ax.grid(True, axis='y', color='gray', linestyle='-', linewidth=0.5, alpha=0.2)

    # Make the y=0 line barely visible
    ax.axhline(0, color='gray', linestyle='-', linewidth=1, alpha=0.6)
#.........................................................................
def create_covid_summary_plot(dfs, width_mm=210, height_mm=126):

    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs.iloc[-1][[
        "potvrzene_pripady_vcerejsi_den",
        "provedene_testy_vcerejsi_den",
        "vykazana_ockovani_vcerejsi_den",
        "potvrzene_pripady_65_vcerejsi_den",
        "reinfekce_vcerejsi_den",
        "ockovane_osoby_vcerejsi_den"
    ]]

    custom_labels = {
        "potvrzene_pripady_vcerejsi_den": "Potvrzené případy",
        "provedene_testy_vcerejsi_den": "Provedené testy",
        "vykazana_ockovani_vcerejsi_den": "Vykázaná očkování",
        "potvrzene_pripady_65_vcerejsi_den": "Potvrzené případy 65+",
        "reinfekce_vcerejsi_den": "Reinfekce",
        "ockovane_osoby_vcerejsi_den": "Očkované osoby"
    }

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    ax.axis('off')

    positions = [ # positions of the rectangles and text
        (0.1, 0.78), (0.5, 0.78),
        (0.1, 0.58), (0.5, 0.58),
        (0.1, 0.38), (0.5, 0.38)
    ]

    # width and height for all rectangles
    rect_width = 0.37
    rect_height = 0.15

    ax.text(0.48, 0.9, 'Včera', ha='center', va='center', fontsize=12, fontweight='bold') # custom text

    # Iterate over each value in the series and plot the fixed-size rectangles and text
    for (x, y), (column, value) in zip(positions, df.items()):
        label = custom_labels.get(column, column) # Get the custom label for each column

        # Draw a fixed-size rectangle at the given position
        rect = Rectangle((x, y - rect_height / 2), rect_width, rect_height, linewidth=1, edgecolor='black', facecolor='white')
        ax.add_patch(rect)

        # Display custom label and value inside the rectangle
        ax.text(x + rect_width / 2, y + 0.03, f'{label}', ha='center', va='center', fontsize=11, color='black')
        ax.text(x + rect_width / 2, y - 0.03, f'{value}', ha='center', va='center', fontsize=20, fontweight='bold', color='black')

    fig.savefig("obr_zakl1.png", format="png", dpi=300) #, bbox_inches='tight'

    fig = plt.gcf()
    plt.close(fig)

    return fig
#.........................................................................................

def create_covid_summary_plot2(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs.iloc[-1][[
        "aktivni_pripady",
        "aktualne_hospitalizovani",
        "provedene_testy_celkem",
        "potvrzene_pripady_celkem",
        "umrti",
        "ockovane_osoby_celkem",
        "potvrzene_pripady_65_celkem",
        "reinfekce_celkem"
    ]]

    custom_labels = {
        "aktivni_pripady": "Aktivní případy",
        "aktualne_hospitalizovani": "Aktuálně hospitalizovaní",
        "provedene_testy_celkem": "Provedené testy",
        "potvrzene_pripady_celkem": "Potvrzené případy",
        "umrti": "Úmrtí",
        "ockovane_osoby_celkem": "Očkované osoby",
        "potvrzene_pripady_65_celkem": "Potvrzené případy 65+",
        "reinfekce_celkem": "Reinfekce"
    }

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    ax.axis('off')

    positions = [
        (0.1, 0.78), (0.5, 0.78),
        (0.1, 0.5), (0.5, 0.5),
        (0.1, 0.3), (0.5, 0.3),
        (0.1, 0.1), (0.5, 0.1)
    ]

    rect_width = 0.37
    rect_height = 0.15

    ax.text(0.48, 0.9, 'Aktivní', ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(0.48, 0.63, 'Celkem', ha='center', va='center', fontsize=12, fontweight='bold')

    for (x, y), (column, value) in zip(positions, df.items()):
        label = custom_labels.get(column, column)

        rect = Rectangle((x, y - rect_height / 2), rect_width, rect_height, linewidth=1, edgecolor='black', facecolor='white')
        ax.add_patch(rect)

        ax.text(x + rect_width / 2, y + 0.03, f'{label}',  ha='center', va='center', fontsize=11, color='black')
        ax.text(x + rect_width / 2, y - 0.03, f'{value}', ha='center', va='center', fontsize=20, fontweight='bold', color='black')

    fig.savefig("obr_zakl2.png", format="png", dpi=300)

    fig = plt.gcf()
    plt.close(fig)

    return fig
#..........................................................................................

def plot_infection_trends(df, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = df.drop_duplicates()
    df.loc[:, 'datum'] = pd.to_datetime(df['datum'])
    df = df.sort_values(by='datum')

    df['sum_category_A'] = df['prirustkovy_pocet_nove_nakazenych_primoinfekce'].rolling(window=7).sum()
    df['sum_category_B'] = df['prirustkovy_pocet_nove_nakazenych_reinfekce'].rolling(window=7).sum()

    df['stacked_B'] = df['sum_category_A'] + df['sum_category_B']

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    # Plot Category B as a stacked line, on top of Category A
    ax.plot(df['datum'], df['stacked_B'], label='Reinfekce', color='#ff7f0e', linewidth=0.2)

    # Fill the area between Category A and the stacked Category B
    ax.fill_between(df['datum'], df['sum_category_A'], df['stacked_B'], color='#ff7f0e', alpha=0.9)

    # Fill the area between 0 and Category A (base)
    ax.fill_between(df['datum'], 0, df['sum_category_A'], color='#1f77b4', alpha=0.4)

    # Plot Category A as the base line (after the fill to make it more prominent)
    ax.plot(df['datum'], df['sum_category_A'], label='Primoinfekce', color='#1f77b4', linewidth=0.9)

    # Add rectangle from 33 days ago to the most recent date
    end_date = df['datum'].max()
    start_date = end_date - pd.Timedelta(days=33)
    ax.axvspan(start_date, end_date, ymin=0, ymax=40000 / df['stacked_B'].max(), edgecolor='black', fill=False, linewidth=1)

    ax.set_title('Přírůstkový počet nově nakažených (7denní klouzavý součet)')

    # Function to format y-axis values
    def thousands_formatter(x, pos):
        return f'{int(x / 1000)} tis.'
    ax.yaxis.set_major_formatter(FuncFormatter(thousands_formatter))

    format_plot(ax)

    # Add legend below the x-axis
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3, frameon=False)
    plt.subplots_adjust(bottom=0.25)

    # plt.tight_layout()
    plt.savefig("obr_0_0.png", format="png", dpi=300)

    fig = plt.gcf()  # Get the current figure
    plt.close(fig)  # Close the figure to prevent it from being shown automatically

    print("Vytvořen obrázek 1")
    return fig
#.......................................................................................

def plot_covid_cases(df, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = df.drop_duplicates()
    df.loc[:, 'datum'] = pd.to_datetime(df['datum'])
    df = df.sort_values(by='datum')
    df = df[df['datum'] >= (df['datum'].max() - pd.Timedelta(days=34))]

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    bar1 = ax.bar(df['datum'], df['prirustkovy_pocet_nove_nakazenych_primoinfekce'], label='Primoinfekce')
    bar2 = ax.bar(df['datum'], df['prirustkovy_pocet_nove_nakazenych_reinfekce'], bottom=df['prirustkovy_pocet_nove_nakazenych_primoinfekce'], label='Reinfekce')

    # Set the locator for Mondays only on the x-axis
    mondays = mdates.WeekdayLocator(byweekday=mdates.MO)
    ax.xaxis.set_major_locator(mondays)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))

    ax.set_title('Přírůstkový počet nově nakažených')

    format_plot(ax)

    # Add legend below the x-axis
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3, frameon=False)
    fig.subplots_adjust(bottom=0.25)

    # Add values to the last 7 bars
    last_7 = df.tail(7)  # Extract the last 7 data points
    for i, (bar1_rect, bar2_rect, (index, row)) in enumerate(zip(bar1[-7:], bar2[-7:], last_7.iterrows())):
        # Values for Primoinfekce
        primoinfekce_value = row['prirustkovy_pocet_nove_nakazenych_primoinfekce']
        ax.text(bar1_rect.get_x() + bar1_rect.get_width() / 2, bar1_rect.get_height() / 2,
                f'{int(primoinfekce_value)}', ha='center', va='bottom', color='black', fontsize=6)

        # Values for Reinfekce
        reinfekce_value = row['prirustkovy_pocet_nove_nakazenych_reinfekce']
        ax.text(bar2_rect.get_x() + bar2_rect.get_width() / 2,
                bar1_rect.get_height() + (bar2_rect.get_height() / 2),
                f'{int(reinfekce_value)}', ha='center', va='bottom', color='black', fontsize=6)

    fig.savefig("obr_1_0.png", format="png", dpi=300)

    fig = plt.gcf()
    plt.close(fig)

    print("Vytvořen obrázek 2")
    return fig
#.....................................................................

def plot_cumulative_graph(df, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = df.drop_duplicates()
    df.loc[:, 'datum'] = pd.to_datetime(df['datum'])
    df = df.sort_values(by='datum')

    # Custom formatter for the y-axis
    def format_func(value, tick_number):
        return f'{value * 1e-6:.0f} mil.'  # Convert to 'e6' format with whole numbers

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    ax.plot(df['datum'], df['kumulativni_pocet_testu'], label='Počet testů')
    ax.plot(df['datum'], df['kumulativni_pocet_nakazenych'], label='Počet nakažených')
    ax.plot(df['datum'], df['kumulativni_pocet_umrti'], label='Počet úmrtí')

    ax.set_title('Kumulativní přehled počtu testů, nakažených a úmrtí')

    format_plot(ax)

    # Add legend below the x-axis
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3, frameon=False)
    fig.subplots_adjust(bottom=0.25)

    # Apply custom y-axis formatting and set desired ticks
    ax.yaxis.set_major_formatter(FuncFormatter(format_func))

    #fig.tight_layout()

    fig.savefig("obr_0_1.png", format="png", dpi=300)

    fig = plt.gcf()
    plt.close(fig)

    print("Vytvořen obrázek 3")
    return fig
#.............................................................................

def plot_new_cases_and_deaths(df, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = df.drop_duplicates()
    df.loc[:, 'datum'] = pd.to_datetime(df['datum'])
    df = df.sort_values(by='datum')
    df = df[df['datum'] >= (df['datum'].max() - pd.Timedelta(days=34))]

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    # Define bar width and adjust x positions to display bars side by side
    bar_width = 0.4
    x1 = df['datum'] - pd.Timedelta(days=bar_width / 2)  # Shift for the first set of bars
    x2 = df['datum'] + pd.Timedelta(days=bar_width / 2)  # Shift for the second set of bars

    # Plot the bars for each value
    bar1 = ax.bar(x1, df['prirustkovy_pocet_nakazenych'], width=bar_width, label='Nové případy')
    bar2 = ax.bar(x2, df['prirustkovy_pocet_umrti'], width=bar_width, label='Nová úmrtí')

    # Set the locator for Mondays only on the x-axis
    mondays = mdates.WeekdayLocator(byweekday=mdates.MO)
    ax.xaxis.set_major_locator(mondays)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))

    ax.set_title('Přírůstkový počet nakažených a úmrtí')

    # Get the last 7 values from each series
    last_7_nakazenych = df['prirustkovy_pocet_nakazenych'].tail(7)
    last_7_umrti = df['prirustkovy_pocet_umrti'].tail(7)
    last_7_dates = df['datum'].tail(7)

    format_plot(ax)

    # Place the legend below the plot, in one line, without a border
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, frameon=False)

    # Add value annotations to the last 7 bars for both series
    for i in range(7):
        ax.text(last_7_dates.iloc[i] - pd.Timedelta(days=bar_width / 2), last_7_nakazenych.iloc[i] + 10,
                f'{last_7_nakazenych.iloc[i]}', ha='center', va='bottom')

        ax.text(last_7_dates.iloc[i] + pd.Timedelta(days=bar_width / 2), last_7_umrti.iloc[i] + 10,
                f'{last_7_umrti.iloc[i]}', ha='center', va='bottom')

    #plt.tight_layout()
    fig.savefig("obr_nevim.png", format="png", dpi=300)

    fig = plt.gcf()
    plt.close(fig)

    print("Vytvořen obrázek 4")

    return fig
#.................................................................................
def plot_incidence_map(df, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    # Function to load GPS coordinates from a text file
    def load_gps_coordinates(file_path):
        with open(file_path, 'r') as file:
            coordinates = json.loads(file.read())
            return [(lat, lon) for lat, lon in coordinates[0]]

    region_files = [f"gps_souradnice_kraju/kraj{i}.txt" for i in range(0, 14)]  # "kraj0.txt", ..., "kraj13.txt"
    regions = []

    # Load each region and create a polygon
    for region_file in region_files:
        coordinates = load_gps_coordinates(region_file)
        polygon = Polygon(coordinates)
        regions.append(polygon)

    # Create a GeoDataFrame for regions
    gdf = gpd.GeoDataFrame({'geometry': regions}, crs="EPSG:4326")

    # According to this list, the names of regions are matched to the txt files with coordinates
    region_names = [
        'Hlavní město Praha', 'Středočeský kraj', 'Jihočeský kraj', 'Plzeňský kraj',
        'Karlovarský kraj', 'Ústecký kraj', 'Liberecký kraj', 'Královéhradecký kraj',
        'Pardubický kraj', 'Kraj Vysočina', 'Jihomoravský kraj', 'Olomoucký kraj',
        'Zlínský kraj', 'Moravskoslezský kraj'
    ]

    gdf['kraj_nazev'] = region_names

    df = df.loc[
        (df.datum == df.datum.max()) & (df.kraj_nazev.notna()),
        ["kraj_nazev", "incidence_7_100000"]
    ]
    gdf = gdf.merge(df, on='kraj_nazev')

    # Plot the map, coloring by the 'incidence_7_100000' values
    fig, ax = plt.subplots(figsize=(width_inch, height_inch))
    gdf.plot(
        column='incidence_7_100000',
        cmap='Reds',
        linewidth=0.8,
        ax=ax,
        edgecolor='black',
        legend=True,
        alpha=0.8,
        legend_kwds={
            'shrink': 0.7,    # Shrink the size of the legend
            'aspect': 20,     # Adjust aspect ratio (how tall and narrow the color bar is)
            # 'label': 'Incidence 7/100,000',  # Custom label for the legend
            'format': '%.0f'  # Limit decimal places in legend ticks
        }
    )

    ax.set_title('Nové případy za posledních 7 dnů (na 100 000 obyvatel)')
    ax.axis('off')

    fig.savefig("obr_0_2.png", format="png", dpi=300)

    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 5")

    return fig
#........................................................................
def plot_incidence_map14(df, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    def load_gps_coordinates(file_path):
        with open(file_path, 'r') as file:
            coordinates = json.loads(file.read())
            return [(lat, lon) for lat, lon in coordinates[0]]

    region_files = [f"gps_souradnice_kraju/kraj{i}.txt" for i in range(0, 14)]
    regions = []

    # Load each region and create a polygon
    for region_file in region_files:
        coordinates = load_gps_coordinates(region_file)
        polygon = Polygon(coordinates)
        regions.append(polygon)

    # Create a GeoDataFrame for regions
    gdf = gpd.GeoDataFrame({'geometry': regions}, crs="EPSG:4326")

    # According to this list, the names of regions are matched to the txt files with coordinates
    region_names = [
        'Hlavní město Praha', 'Středočeský kraj', 'Jihočeský kraj', 'Plzeňský kraj',
        'Karlovarský kraj', 'Ústecký kraj', 'Liberecký kraj', 'Královéhradecký kraj',
        'Pardubický kraj', 'Kraj Vysočina', 'Jihomoravský kraj', 'Olomoucký kraj',
        'Zlínský kraj', 'Moravskoslezský kraj'
    ]

    gdf['kraj_nazev'] = region_names

    df = df.loc[
        (df.datum == df.datum.max()) & (df.kraj_nazev.notna()),
        ["kraj_nazev", "incidence_14_100000"]
    ]
    gdf = gdf.merge(df, on='kraj_nazev')

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))
    gdf.plot(
        column='incidence_14_100000',
        cmap='Reds',
        linewidth=0.8,
        ax=ax,
        edgecolor='black',
        legend=True,
        alpha=0.8,
        legend_kwds={
            'shrink': 0.7,    # Shrink the size of the legend
            'aspect': 20,     # Adjust aspect ratio (how tall and narrow the color bar is)
            # 'label': 'Incidence 7/100,000',  # Custom label for the legend
            'format': '%.0f'  # Limit decimal places in legend ticks
        }
    )

    ax.set_title('Nové případy za posledních 14 dnů (na 100 000 obyvatel)')
    ax.axis('off')

    fig.savefig("obr_1_2.png", format="png", dpi=300)

    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 6")
    return fig
#.........................................................................................

def create_stacked_plot(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs
    df['datum'] = pd.to_datetime(df['datum'])
    df = df.sort_values(by='datum')

    df['sum_category_A'] = df['stav_bez_priznaku'].rolling(window=7).sum()
    df['sum_category_B'] = df['stav_lehky'].rolling(window=7).sum()
    df['sum_category_C'] = df['stav_stredni'].rolling(window=7).sum()
    df['sum_category_D'] = df['stav_tezky'].rolling(window=7).sum()

    # Create a stacked effect by summing the categories
    df['stacked_B'] = df['sum_category_A'] + df['sum_category_B']
    df['stacked_C'] = df['stacked_B'] + df['sum_category_C']
    df['stacked_D'] = df['stacked_C'] + df['sum_category_D']

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    # Plot Category D (on top of all others)
    ax.plot(df['datum'], df['stacked_D'], label='těžký stav', color='#d62728', linewidth=0.2)
    ax.fill_between(df['datum'], df['stacked_C'], df['stacked_D'], color='#d62728', alpha=0.9)

    # Plot Category C
    ax.plot(df['datum'], df['stacked_C'], label='střední stav', color='#2ca02c', linewidth=0.2)
    ax.fill_between(df['datum'], df['stacked_B'], df['stacked_C'], color='#2ca02c', alpha=0.7)

    # Plot Category B
    ax.plot(df['datum'], df['stacked_B'], label='lehký stav', color='#ff7f0e', linewidth=0.2)
    ax.fill_between(df['datum'], df['sum_category_A'], df['stacked_B'], color='#ff7f0e', alpha=0.5)

    # Plot Category A (base)
    ax.plot(df['datum'], df['sum_category_A'], label='bez příznaků', color='#1f77b4', linewidth=0.9)
    ax.fill_between(df['datum'], 0, df['sum_category_A'], color='#1f77b4', alpha=0.4)

    # Add rectangle from 33 days ago to the most recent date
    end_date = df['datum'].max()
    start_date = end_date - pd.Timedelta(days=33)

    ax.axvspan(start_date, end_date, ymin=0, ymax=10000 / df['stacked_D'].max(), edgecolor='black', fill=False,
               linewidth=1)

    ax.set_title('Počet a stav hospitalizovaných (7denní klouzavý součet)')
    ax.legend()

    format_plot(ax)

    # Add legend below the x-axis
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=4, frameon=False)
    plt.subplots_adjust(bottom=0.25)

    #plt.tight_layout()
    plt.savefig("obr_0_3.png", format="png", dpi=300)

    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 7")

    return fig
#.................................................................................

def create_stacked_bar_chart(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs
    df['datum'] = pd.to_datetime(df['datum'])
    df = df.sort_values(by='datum')
    df = df[df['datum'] >= (df['datum'].max() - pd.Timedelta(days=34))]

    df.set_index('datum', inplace=True)

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    # Initialize the bottom variable to zeros (to handle the stacking)
    bottom = pd.Series([0] * len(df), index=df.index)

    custom_labels = {
        'stav_bez_priznaku': 'bez příznaků',
        'stav_lehky': 'lehký stav',
        'stav_stredni': 'střední stav',
        'stav_tezky': 'těžký stav',
    }

    # Loop through each column and stack bars
    for column in df.columns:
        label = custom_labels.get(column, column)
        ax.bar(df.index, df[column], bottom=bottom, label=label)

        for i, value in enumerate(df[column].iloc[-7:]):
            day = df.index[-7:][i]
            ax.text(day, bottom.iloc[-7 + i] + value / 2, f'{value:.0f}', ha='center', va='center', fontsize=6)

        bottom += df[column]  # Update the bottom for the next bar

    ax.set_title('Počet a stav hospitalizovaných')

    ax.legend()

    # Set the locator for Mondays only on the x-axis
    mondays = mdates.WeekdayLocator(byweekday=mdates.MO)
    plt.gca().xaxis.set_major_locator(mondays)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))

    format_plot(ax)

    # Add legend below the x-axis
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=4, frameon=False)
    plt.subplots_adjust(bottom=0.25)

    plt.savefig("obr_1_3.png", format="png", dpi=300)
    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 8")

    return fig

#.........................................................................

def create_percentage_stacked_plot(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs
    df['datum'] = pd.to_datetime(df['datum'])
    df = df.sort_values(by='datum')

    df['sum_category_A'] = df['stav_bez_priznaku'].rolling(window=7).sum()
    df['sum_category_B'] = df['stav_lehky'].rolling(window=7).sum()
    df['sum_category_C'] = df['stav_stredni'].rolling(window=7).sum()
    df['sum_category_D'] = df['stav_tezky'].rolling(window=7).sum()

    # Calculate the total sum of all categories for each day
    df['total_sum'] = df[['sum_category_A', 'sum_category_B', 'sum_category_C', 'sum_category_D']].sum(axis=1)

    # Convert each category to percentage of the total sum
    df['perc_category_A'] = (df['sum_category_A'] / df['total_sum']) * 100
    df['perc_category_B'] = (df['sum_category_B'] / df['total_sum']) * 100
    df['perc_category_C'] = (df['sum_category_C'] / df['total_sum']) * 100
    df['perc_category_D'] = (df['sum_category_D'] / df['total_sum']) * 100

    # Create a stacked effect by summing the percentage categories
    df['stacked_B_perc'] = df['perc_category_A'] + df['perc_category_B']
    df['stacked_C_perc'] = df['stacked_B_perc'] + df['perc_category_C']
    df['stacked_D_perc'] = df['stacked_C_perc'] + df['perc_category_D']

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    # Plot Category D (on top of all others)
    ax.plot(df['datum'], df['stacked_D_perc'], label='těžký stav', color='#d62728', linewidth=0.2)
    ax.fill_between(df['datum'], df['stacked_C_perc'], df['stacked_D_perc'], color='#d62728', alpha=0.9)

    # Plot Category C
    ax.plot(df['datum'], df['stacked_C_perc'], label='střední stav', color='#2ca02c', linewidth=0.2)
    ax.fill_between(df['datum'], df['stacked_B_perc'], df['stacked_C_perc'], color='#2ca02c', alpha=0.7)

    # Plot Category B
    ax.plot(df['datum'], df['stacked_B_perc'], label='lehký stav', color='#ff7f0e', linewidth=0.2)
    ax.fill_between(df['datum'], df['perc_category_A'], df['stacked_B_perc'], color='#ff7f0e', alpha=0.5)

    # Plot Category A (base)
    ax.plot(df['datum'], df['perc_category_A'], label='bez příznaků', color='#1f77b4', linewidth=0.9)
    ax.fill_between(df['datum'], 0, df['perc_category_A'], color='#1f77b4', alpha=0.4)

    ax.set_title('Počet a stav hospitalizovaných (7denní klouzavý součet) v procentech')
    ax.legend()

    format_plot(ax)

    # Add legend below the x-axis
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=4, frameon=False)
    plt.subplots_adjust(bottom=0.25)

    # Save the plot
    #plt.tight_layout()
    plt.savefig("obr_0_4.png", format="png", dpi=300)

    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 9")

    return fig
#................................................................................

def create_recent_percentage_stacked_plot(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs.copy()
    df['datum'] = pd.to_datetime(df['datum'])
    df = df.sort_values(by='datum')
    df = df[df['datum'] >= (df['datum'].max() - pd.Timedelta(days=34))]

    df.set_index('datum', inplace=True)

    # Normalize the data to percentage for each day
    df_percentage = df.div(df.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    # Initialize the bottom variable to zeros (to handle the stacking)
    bottom = pd.Series([0] * len(df_percentage), index=df_percentage.index)

    custom_labels = {
        'stav_bez_priznaku': 'bez příznaků',
        'stav_lehky': 'lehký stav',
        'stav_stredni': 'střední stav',
        'stav_tezky': 'těžký stav',
    }

    # Loop through each column and stack bars
    for column in df_percentage.columns:
        label = custom_labels.get(column, column) if custom_labels else column
        ax.bar(df_percentage.index, df_percentage[column], bottom=bottom, label=label)

        for i, value in enumerate(df_percentage[column].iloc[-7:]):  # Use .iloc for positional indexing
            day = df_percentage.index[-7:][i]  # This works fine for positional indexing
            ax.text(day, bottom.iloc[-7 + i] + value / 2, f'{value:.0f}', ha='center', va='center', fontsize=6)

        bottom += df_percentage[column]  # Update the bottom for the next bar

    ax.set_title('Počet a stav hospitalizovaných v procentech')

    ax.legend()

    # Set the locator for Mondays only on the x-axis
    mondays = mdates.WeekdayLocator(byweekday=mdates.MO)
    plt.gca().xaxis.set_major_locator(mondays)

    # Set the formatter to show dates in a readable format (e.g., 'YYYY-MM-DD')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))

    format_plot(ax)

    # Add legend below the x-axis
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=4, frameon=False)
    plt.subplots_adjust(bottom=0.25)

    plt.savefig("obr_1_4.png", format="png", dpi=300)
    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 10")

    return fig
#.............................................................................

def create_hospitalization_jip_ecmo_plot(dfs, width_mm=170, height_mm=102):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs
    df['datum'] = pd.to_datetime(df['datum'], errors='coerce')

    # Filter out rows where 'datum' is NaT
    df = df.dropna(subset=['datum'])
    df['datum'] = pd.to_datetime(df['datum'])

    max_date = df['datum'].max()

    start_date = max_date - pd.Timedelta(days=34)

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    ax.plot(df['datum'], df['pocet_hosp'], label='Akt. počet hospitalizovaných', marker='')
    ax.plot(df['datum'], df['jip'], label='Počet osob na JIP', marker='')
    ax.plot(df['datum'], df['tezky_upv_ecmo'], label='Těžký stav nebo UPV, ECMO', marker='')

    # Convert the dates to matplotlib date numbers
    start_date_num = mdates.date2num(start_date)
    end_date_num = mdates.date2num(max_date)

    # Add rectangle from 33 days ago to the most recent date
    end_date = df['datum'].max()
    start_date = end_date - pd.Timedelta(days=34)

    ax.axvspan(start_date, end_date, ymin=0, ymax=1000/df['pocet_hosp'].max(), edgecolor='black', fill=False, linewidth=1)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    ax.set_title('Počty hospitalizovaných')
    ax.legend()

    format_plot(ax)

    # Add legend below the x-axis
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3, frameon=False)
    plt.subplots_adjust(bottom=0.25)

    ax.set_ylim([-10, 10000])

    plt.tight_layout()
    plt.savefig("obr_0_5.png", format="png", dpi=360)
    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 11")

    return fig
#.................................................................................

def create_jip_ecmo_last_14_days_plot(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs

    df['datum'] = pd.to_datetime(df['datum'], errors='coerce')

    # Filter out rows where 'datum' is NaT
    df = df.dropna(subset=['datum'])

    last_14_days = df[df['datum'] >= (df['datum'].max() - pd.Timedelta(days=34))]
    last_7_days = df[df['datum'] >= (df['datum'].max() - pd.Timedelta(days=6))]

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    ax.plot(last_14_days['datum'], last_14_days['pocet_hosp'], label='Akt. počet hospitalizovaných', marker='o', markersize=3)
    ax.plot(last_14_days['datum'], last_14_days['jip'], label='Počet osob na JIP', marker='o', markersize=3)
    ax.plot(last_14_days['datum'], last_14_days['tezky_upv_ecmo'], label='Těžký stav nebo UPV, ECMO', marker='o', markersize=3)

    ax.set_xlim(last_14_days['datum'].min(), last_14_days['datum'].max() + pd.Timedelta(days=1))

    ax.set_title('Počty hospitalizovaných')

    # Restore the y-axis label and add barely visible horizontal lines
    ax.yaxis.set_visible(True)
    ax.yaxis.set_ticks_position('none')  # Removes y-axis ticks but keeps the labels
    ax.grid(True, axis='y', color='gray', linestyle='-', linewidth=0.5, alpha=0.2)

    format_plot(ax)

    # Place the legend below the plot, without a box, and in one line
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3, frameon=False)

    # Set the locator for Mondays only on the x-axis
    mondays = mdates.WeekdayLocator(byweekday=mdates.MO)
    plt.gca().xaxis.set_major_locator(mondays)

    # Set the formatter to show dates in a readable format (e.g., 'YYYY-MM-DD')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))

    # Add vertical lines for each Monday
    for monday in last_14_days['datum'].loc[last_14_days['datum'].dt.weekday == 0]:
        ax.axvline(x=monday, color='gray', linestyle='--', linewidth=0.8, alpha=0.2)

    # Annotate the last 7 days of data with values for each line
    for i, row in last_7_days.iterrows():
        ax.annotate(f'{row["pocet_hosp"]:.0f}', (row['datum'], row['pocet_hosp']), textcoords="offset points",
                    xytext=(0, 5), ha='center', fontsize=8, color='blue')
        ax.annotate(f'{row["jip"]:.0f}', (row['datum'], row['jip']), textcoords="offset points", xytext=(0, 5),
                    ha='center', fontsize=8, color='green')
        ax.annotate(f'{row["tezky_upv_ecmo"]:.0f}', (row['datum'], row['tezky_upv_ecmo']), textcoords="offset points",
                    xytext=(0, 5), ha='center', fontsize=8, color='red')

    #plt.tight_layout()

    plt.savefig("obr_1_5.png", format="png", dpi=300)
    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 12")

    return fig
#......................................................................................

def create_vaccination_trend_plot(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs.groupby(["datum", "poradi_davky"])["pocet_davek"].sum().to_frame("count").reset_index()

    df['datum'] = pd.to_datetime(df['datum'])

    pivot_df = df.pivot(index='datum', columns='poradi_davky', values='count').fillna(0)

    pivot_df_rolling = pivot_df.rolling(window=7).mean()

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564', '#e377c2', '#7f7f7f', '#bcbd22',
              '#17becf']
    custom_colors = colors[:3] + ['#d62728', '#9467bd', 'yellow'] + colors[6:]

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    # Plotting the stacked area chart of 7-day moving average
    pivot_df_rolling.plot(kind='area', stacked=True, ax=ax, color=custom_colors, alpha=0.8)

    ax.set_title("Počet dávek v závislosti na jejich pořadí")

    # Remove axis labels
    ax.set_xlabel("")
    ax.set_ylabel("")

    ax.set_xlim(pd.Timestamp('2020-01-01'), pd.Timestamp('2025-01-01'))

    # Set the major ticks to year intervals and format the ticks to display only the year
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    plt.xticks(rotation=0, ha='center') #, fontsize=10

    # Add gridlines for better readability
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)

    # Function to format y-axis values
    def thousands_formatter(x, pos):
        return f'{int(x / 1000)} tis.'
    ax.yaxis.set_major_formatter(FuncFormatter(thousands_formatter))

    # Add rectangle from 33 days ago to the most recent date
    end_date = df['datum'].max()
    start_date = end_date - pd.Timedelta(days=33)
    ax.axvspan(start_date, end_date, ymin=0, ymax=0.15, edgecolor='black', fill=False, linewidth=1)

    format_plot(ax)

    # Customize the legend and place it below the plot
    ax.legend(
        title="Pořadí dávky",
        bbox_to_anchor=(0.5, -0.05),
        loc='upper center',
        ncol=9,  # Place the legend into two lines
        #fontsize=10,
        #title_fontsize=12,
        frameon=False  # Remove the border
    )

    #plt.tight_layout()

    plt.savefig("obr_0_6.png", format="png", dpi=300)

    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 13")

    return fig
#..............................................................................

def create_vaccination_last_month_plot(dfs, width_mm=210, height_mm=126):

    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs
    df['datum'] = pd.to_datetime(df['datum'])
    df = df.sort_values(by='datum')
    df = df[df['datum'] >= (df['datum'].max() - pd.Timedelta(days=36))]

    df = df.groupby(["datum", "poradi_davky"])["pocet_davek"].sum().to_frame("count").reset_index()

    pivot_df = df.pivot(index='datum', columns='poradi_davky', values='count').fillna(0)

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564', '#e377c2', '#7f7f7f', '#bcbd22',
              '#17becf']
    custom_colors = colors[:3] + ['#d62728', '#9467bd', 'yellow'] + colors[6:]

    # Create the stacked bar chart
    fig, ax = plt.subplots(figsize=(width_inch, height_inch))
    pivot_df.plot(kind='bar', stacked=True, ax=ax, color=custom_colors)

    ax.set_title("Počet dávek v závislosti na jejich pořadí")

    ax.legend(title="Dose Number")

    ax.set_xlabel("")
    ax.set_ylabel("")

    # Function to format y-axis values
    def thousands_formatter(x, pos):
        return f'{int(x / 1000)} tis.'
    ax.yaxis.set_major_formatter(FuncFormatter(thousands_formatter))

    # Set x-axis labels to show only Mondays
    mondays = pivot_df.index[pivot_df.index.weekday == 0]
    ax.set_xticks([pivot_df.index.get_loc(date) for date in mondays])
    ax.set_xticklabels([date.strftime('%d.%m') for date in mondays], rotation=0)

    format_plot(ax)

    # Customize the legend and place it below the plot
    ax.legend(
        title="Pořadí dávky",
        bbox_to_anchor=(0.5, -0.05),
        loc='upper center',
        ncol=9,  # Place the legend into two lines
        #fontsize=10,
        #title_fontsize=12,
        frameon=False  # Remove the border
    )

    plt.tight_layout()

    plt.savefig("obr_1_6.png", format="png", dpi=300)
    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 14")

    return fig
#..................................................................

def create_vaccine_doses_by_type_plot(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs
    grouped_data = df.groupby('vakcina')['pocet_davek'].sum().sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))
    grouped_data.plot(kind='barh', ax=ax)

    ax.set_title('Počty dávek dle vakcín')

    ax.invert_yaxis()

    format_plot(ax)

    def format_func(value, tick_number):
        return f'{value * 1e-6:.0f} mil.'  # Convert to 'e6' format with whole numbers
    ax.xaxis.set_major_formatter(FuncFormatter(format_func))

    # Set ticks but without grid lines
    ax.xaxis.set_visible(True)
    ax.xaxis.set_ticks_position('none')  # Removes x-axis ticks but keeps the labels
    ax.grid(True, axis='x', color='gray', linestyle='-', linewidth=0.5, alpha=0.2)
    ax.yaxis.set_ticks_position('none')
    ax.grid(False, axis='y')

    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)

    ax.set_xlabel("")
    ax.set_ylabel("")

    plt.tight_layout()

    plt.savefig("obr_0_7.png", format="png", dpi=300)
    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 15")

    return fig
#...........................................................................

def create_doses_by_dose_number_plot(df, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    grouped_data = df.groupby('poradi_davky')['pocet_davek'].sum().sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))
    bars = grouped_data.plot(kind='bar', ax=ax)

    ax.set_title('Počty dávek dle pořadí dávky')

    format_plot(ax)

    def format_func(value, tick_number):
        return f'{value * 1e-6:.0f} mil.'  # Convert to 'e6' format with whole numbers
    ax.yaxis.set_major_formatter(FuncFormatter(format_func))

    # Set ticks but without grid lines
    ax.yaxis.set_visible(True)
    ax.yaxis.set_ticks_position('none')  # Removes y-axis ticks but keeps the labels
    ax.grid(True, axis='y', color='gray', linestyle='-', linewidth=0.5, alpha=0.2)
    ax.xaxis.set_ticks_position('none')

    # Add values on top of each bar
    for bar in bars.patches:
        height = bar.get_height()
        ax.annotate(f'{height}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')

    ax.set_xlabel("")
    ax.set_ylabel("")

    plt.xticks(rotation=0)

    #plt.tight_layout()

    plt.savefig("obr_1_7.png", format="png", dpi=300)
    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 16")

    return fig
#....................................................................

def plot_vaccine_doses_by_age(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    def categorize_age_group(age_group):
        if age_group in ['0-4', '05-11', '12-15', '16-17', 'nezařazeno']:
            return '0-18'
        elif age_group in ['18-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64']:
            return '19-64'
        elif age_group in ['65-69', '70-74', '75-79', '80+']:
            return '65-80+'
        else:
            return 'unknown'

    dfs['age_category'] = dfs['vekova_skupina'].apply(categorize_age_group)

    df = dfs.loc[:, ["age_category", "pocet_davek", "datum"]]
    df['datum'] = pd.to_datetime(df['datum'])
    df = df.sort_values(by='datum')
    grouped_df = df.groupby(["datum", "age_category"])["pocet_davek"].sum().unstack(fill_value=0)

    rolling_df = grouped_df.rolling(window=7, min_periods=1).sum()

    # percentages for each day (row-wise division)
    percentage_df = rolling_df.div(rolling_df.sum(axis=1), axis=0)
    percentage_df = percentage_df * 100

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))
    percentage_df.plot(kind='area', stacked=True, ax=ax)

    # Hide unnecessary spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    ax.set_xlabel("")
    ax.set_ylabel("")

    ax.set_xlim(pd.Timestamp('2020-01-01'), pd.Timestamp('2025-01-01'))

    # Ensure labels for 2020 and 2025 are included in the x-axis ticks
    first_days_of_year = pd.date_range(start='2020-01-01', end='2025-01-01', freq='YS')
    ax.set_xticks(first_days_of_year)

    # Set the labels for the ticks, ensuring 2020 and 2025 are visible
    ax.set_xticklabels([str(year.year) for year in first_days_of_year], rotation=0, ha='center')

    format_plot(ax)

    # Customize the legend to be below the x-axis, without a border, in a single line
    ax.legend(title='Věková kategorie', bbox_to_anchor=(0.5, -0.05), loc='upper center', ncol=len(percentage_df.columns), frameon=False)

    ax.set_title('Počet dávek v závislosti na věkové kategorii (7denní kluzavý součet) v procentech')

    #plt.tight_layout()
    plt.savefig("obr_19.png", format="png", dpi=300)
    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 17")

    return fig
#......................................................................

def butterfly_chart_vaccination(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs
    df = df.loc[df.vekova_skupina!="nezařazeno",:]
    grouped = df.groupby(['vekova_skupina', 'pohlavi'])['pocet_davek'].sum().unstack()
    grouped = grouped.fillna(0)

    age_groups = grouped.index
    men = grouped['M']
    women = -grouped['Z']  # Inverting women's values to show on the left

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    ax.barh(age_groups, men, color='blue', label='muži')
    ax.barh(age_groups, women, color='pink', label='ženy')

    # Adding values to the bars
    for i, (man_val, woman_val) in enumerate(zip(men, women)):
        ax.text(man_val + 100, i, f'{int(man_val)}', va='center', ha='left', color='black', fontsize=10)
        ax.text(woman_val - 100, i, f'{int(-woman_val)}', va='center', ha='right', color='black', fontsize=10)

    # Removing the borders
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # Adding labels between the bars
    for i, age_group in enumerate(age_groups):
        ax.text(0, i, str(age_group), ha='center', va='center', color='black', fontsize=10)

    # Removing x and y axis labels and ticks
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_title('Počet dávek v závislosti na pohlaví a věkové skpině')

    # Positioning the legend under the x-axis
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.01), ncol=2, frameon=False)

    plt.savefig("obr_20.png", format="png", dpi=300)
    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 18")

    return fig
#................................................................

def create_cumulative_vaccination_plot(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df_sum = dfs.groupby(["datum"])["celkem_davek"].sum().to_frame("sum").reset_index()
    df_sum["datum"] = pd.to_datetime(df_sum["datum"])
    df_sum["cumulative_sum"] = df_sum["sum"].cumsum()

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    ax.plot(df_sum["datum"], df_sum["cumulative_sum"], label='Cumulative Doses')

    # Customizing the x-axis to show only the first day of each year
    ax.xaxis.set_major_locator(mdates.YearLocator())  # Set ticks at the beginning of each year
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))  # Format ticks as 'YYYY'

    ax.set_title('Kumulativní počet dávek')

    def format_func(value, tick_number):
        return f'{value * 1e-6:.0f} mil.'
    ax.yaxis.set_major_formatter(FuncFormatter(format_func))

    ax.grid(False)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # Restore the y-axis label and add barely visible horizontal lines
    ax.xaxis.set_visible(True)
    ax.xaxis.set_ticks_position('none')  # Removes y-axis ticks but keeps the labels
    ax.grid(True, axis='x', color='gray', linestyle='-', linewidth=0.5, alpha=0.2)

    ax.yaxis.set_visible(True)
    ax.yaxis.set_ticks_position('none')  # Removes y-axis ticks but keeps the labels
    ax.grid(True, axis='y', color='gray', linestyle='-', linewidth=0.5, alpha=0.2)

    ax.set_xlim(pd.Timestamp('2020-01-01'), pd.Timestamp('2025-01-01'))

    #plt.tight_layout()
    plt.savefig("obr_0_8.png", format="png", dpi=300)
    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 19")

    return fig
#...................................................................

def create_vaccine_doses_map(df, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    def load_gps_coordinates(file_path):
        with open(file_path, 'r') as file:
            coordinates = json.loads(file.read())
            return [(lat, lon) for lat, lon in coordinates[0]]

    region_files = [f"gps_souradnice_kraju/kraj{i}.txt" for i in range(0, 14)]  # "kraj0.txt", ..., "kraj13.txt"
    regions = []

    for region_file in region_files:
        coordinates = load_gps_coordinates(region_file)
        polygon = Polygon(coordinates)
        regions.append(polygon)

    gdf = gpd.GeoDataFrame({'geometry': regions}, crs="EPSG:4326")

    region_names = [
        'Hlavní město Praha', 'Středočeský kraj', 'Jihočeský kraj', 'Plzeňský kraj',
        'Karlovarský kraj', 'Ústecký kraj', 'Liberecký kraj', 'Královéhradecký kraj',
        'Pardubický kraj', 'Kraj Vysočina', 'Jihomoravský kraj', 'Olomoucký kraj',
        'Zlínský kraj', 'Moravskoslezský kraj'
    ]

    gdf['kraj_nazev'] = region_names

    total_vaccines_per_region = df.groupby(["kraj_nazev"])["celkem_davek"].sum().reset_index()
    gdf = gdf.merge(total_vaccines_per_region, on='kraj_nazev', how='left')

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))
    gdf.plot(
        column='celkem_davek',
        cmap='Blues',
        linewidth=0.8,
        ax=ax,
        edgecolor='black',
        legend=True,
        alpha=0.8,
        legend_kwds={
            'shrink': 0.7,
            'aspect': 20,
            'format': '%.0f'
        }
    )

    ax.set_title('Proočkovanost krajů)')
    ax.axis('off')

    fig.savefig("obr_1_8.png", format="png", dpi=300)

    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 20")

    return fig
#....................................................................

def create_percentage_stacked_plot_ockovani_hosp(dfs, width_mm=210, height_mm=126):
    width_inch = width_mm / 25.4
    height_inch = height_mm / 25.4

    df = dfs
    df['datum'] = pd.to_datetime(df['datum'])
    df = df.sort_values(by='datum')

    df['sum_category_A'] = df['hospitalizovani_bez_ockovani'].rolling(window=7).sum()
    df['sum_category_B'] = df['hospitalizovani_nedokoncene_ockovani'].rolling(window=7).sum()
    df['sum_category_C'] = df['hospitalizovani_dokoncene_ockovani'].rolling(window=7).sum()
    df['sum_category_D'] = df['hospitalizovani_posilujici_davka'].rolling(window=7).sum()

    df['total_sum'] = df[['sum_category_A', 'sum_category_B', 'sum_category_C', 'sum_category_D']].sum(axis=1)

    # percentage
    df['perc_category_A'] = (df['sum_category_A'] / df['total_sum']) * 100
    df['perc_category_B'] = (df['sum_category_B'] / df['total_sum']) * 100
    df['perc_category_C'] = (df['sum_category_C'] / df['total_sum']) * 100
    df['perc_category_D'] = (df['sum_category_D'] / df['total_sum']) * 100

    # Create a stacked effect by summing the percentage categories
    df['stacked_B_perc'] = df['perc_category_A'] + df['perc_category_B']
    df['stacked_C_perc'] = df['stacked_B_perc'] + df['perc_category_C']
    df['stacked_D_perc'] = df['stacked_C_perc'] + df['perc_category_D']

    fig, ax = plt.subplots(figsize=(width_inch, height_inch))

    # Plot Category D (on top of all others)
    ax.plot(df['datum'], df['stacked_D_perc'], label='posilující dávka', color='#d62728', linewidth=0.2)
    ax.fill_between(df['datum'], df['stacked_C_perc'], df['stacked_D_perc'], color='#d62728', alpha=0.9)

    # Plot Category C
    ax.plot(df['datum'], df['stacked_C_perc'], label='dokončené očkování', color='#2ca02c', linewidth=0.2)
    ax.fill_between(df['datum'], df['stacked_B_perc'], df['stacked_C_perc'], color='#2ca02c', alpha=0.7)

    # Plot Category B
    ax.plot(df['datum'], df['stacked_B_perc'], label='nedokončené očkování', color='#ff7f0e', linewidth=0.2)
    ax.fill_between(df['datum'], df['perc_category_A'], df['stacked_B_perc'], color='#ff7f0e', alpha=0.5)

    # Plot Category A (base)
    ax.plot(df['datum'], df['perc_category_A'], label='bez očkování', color='#1f77b4', linewidth=0.9)
    ax.fill_between(df['datum'], 0, df['perc_category_A'], color='#1f77b4', alpha=0.4)

    ax.set_title('Počet a stav hospitalizovaných (7denní klouzavý součet) v procentech')
    ax.legend()

    format_plot(ax)

    # Add legend below the x-axis
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=4, frameon=False)
    plt.subplots_adjust(bottom=0.25)

    ax.set_xlim(pd.Timestamp('2020-01-01'), pd.Timestamp('2025-01-01'))

    # plt.tight_layout()
    plt.savefig("obr_21.png", format="png", dpi=300)
    fig = plt.gcf()
    plt.close(fig)
    print("Vytvořen obrázek 21")

    return fig
#.......................................................................
def generate_all_figures(dfs):
    fig01 = create_covid_summary_plot(dfs["zakladni-prehled"])
    fig02 = create_covid_summary_plot2(dfs["zakladni-prehled"])
    fig1 = plot_infection_trends(dfs["nakazeni-vyleceni-umrti-testy"])
    fig2 = plot_covid_cases(dfs["nakazeni-vyleceni-umrti-testy"])
    fig3 = plot_cumulative_graph(dfs["nakazeni-vyleceni-umrti-testy"])
    fig4 = plot_new_cases_and_deaths(dfs["nakazeni-vyleceni-umrti-testy"])
    fig5 = plot_incidence_map(dfs["incidence-7-14-kraje"])
    fig6 = plot_incidence_map14(dfs["incidence-7-14-kraje"])
    fig7 = create_stacked_plot(dfs["hospitalizace"].loc[:, ["stav_bez_priznaku", "stav_lehky", "stav_stredni", "stav_tezky", "datum"]])
    fig8 = create_stacked_bar_chart(dfs["hospitalizace"].loc[:, ["stav_bez_priznaku", "stav_lehky", "stav_stredni", "stav_tezky", "datum"]])
    fig9 = create_percentage_stacked_plot(dfs["hospitalizace"].loc[:, ["stav_bez_priznaku", "stav_lehky", "stav_stredni", "stav_tezky", "datum"]])
    fig10 = create_recent_percentage_stacked_plot(dfs["hospitalizace"].loc[:, ["stav_bez_priznaku", "stav_lehky", "stav_stredni", "stav_tezky", "datum"]])
    fig11 = create_hospitalization_jip_ecmo_plot(dfs["hospitalizace"])
    fig12 = create_jip_ecmo_last_14_days_plot(dfs["hospitalizace"])
    fig13 = create_vaccination_trend_plot(dfs["ockovani-demografie"])
    fig14 = create_vaccination_last_month_plot(dfs["ockovani-demografie"])
    fig15 = create_vaccine_doses_by_type_plot(dfs["ockovani-demografie"])
    fig16 = create_doses_by_dose_number_plot(dfs["ockovani-demografie"])
    fig19 = plot_vaccine_doses_by_age(dfs["ockovani-demografie"])
    fig20 = butterfly_chart_vaccination(dfs["ockovani-demografie"])
    fig17 = create_cumulative_vaccination_plot(dfs["ockovani"])
    fig18 = create_vaccine_doses_map(dfs["ockovani"])
    fig21 = create_percentage_stacked_plot_ockovani_hosp(dfs["ockovani-hospitalizace"].loc[:, ["hospitalizovani_bez_ockovani", "hospitalizovani_nedokoncene_ockovani", "hospitalizovani_dokoncene_ockovani", "hospitalizovani_posilujici_davka", "datum"]])



