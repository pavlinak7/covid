from stazeni_dat import *
from vizualizace import *
from vytvoreni_PDF__poslani_emailu import *

import configparser
import math
import glob

############################################### stažení dat/aktualizace ########################################################################
config = load_config('config.ini')

logger = setup_logging() # Setup logging

client = MongoClient(config['mongodb']['uri'])
db = client[config['mongodb']['database']]

session = setup_session(config) # Setup HTTP session with retry strategy

db_list = client.list_database_names() # Check existing databases

if config['mongodb']['database'] not in db_list:
    #yesterday = datetime.today() - timedelta(days=1)
    #yesterday_date = yesterday.strftime('%Y-%m-%d')
    save_all_schemas(config, db, session, logger, some_date = '2024-10-22') #pokud není zadané some_date, tak se stáhne všechno
else:
    two_days_ago = datetime.today() - timedelta(days=2)
    two_days_ago_date = two_days_ago.strftime('%Y-%m-%d')
    today = datetime.today()
    today_date = today.strftime('%Y-%m-%d')
    save_all_schemas(config, db, session, logger, update_date=two_days_ago_date, end_date= today_date) #, update_date="2024-10-10"
    print("----------------------------------------------------------------------------------------")

    ############################################### obrázky ########################################################################
    mongo_uri = "mongodb://localhost:27017/"
    db_name = "covid"
    fields_to_include = {
        'hospitalizace': ['datum', 'pocet_hosp', 'stav_bez_priznaku', 'stav_lehky', 'stav_stredni', 'stav_tezky', 'jip', 'tezky_upv_ecmo'],
        'incidence-7-14-cr': ['datum'],
        'incidence-7-14-kraje': ['datum', 'kraj_nazev', 'incidence_7_100000', 'incidence_14_100000'],
        'nakazeni-vyleceni-umrti-testy': ['datum', 'kumulativni_pocet_nakazenych', 'kumulativni_pocet_umrti', 'kumulativni_pocet_testu',
                                          'prirustkovy_pocet_nakazenych', 'prirustkovy_pocet_umrti',
                                          'prirustkovy_pocet_nove_nakazenych_primoinfekce', 'prirustkovy_pocet_nove_nakazenych_reinfekce'],
        'ockovani': ['datum', 'vakcina', 'celkem_davek', "kraj_nazev"],
        'ockovani-demografie': ['datum', 'poradi_davky', 'vekova_skupina', 'pohlavi', 'pocet_davek', 'vakcina'],
        'ockovani-hospitalizace': ['datum', 'hospitalizovani_bez_ockovani', 'hospitalizovani_nedokoncene_ockovani',
                                   'hospitalizovani_dokoncene_ockovani', "hospitalizovani_posilujici_davka"],
        'zakladni-prehled': ["aktivni_pripady","aktualne_hospitalizovani","provedene_testy_celkem","potvrzene_pripady_celkem",
                            "umrti","ockovane_osoby_celkem","potvrzene_pripady_65_celkem","reinfekce_celkem", "potvrzene_pripady_vcerejsi_den",
                             "provedene_testy_vcerejsi_den", "vykazana_ockovani_vcerejsi_den", "potvrzene_pripady_65_vcerejsi_den", "reinfekce_vcerejsi_den",
                             "ockovane_osoby_vcerejsi_den"]
                        }

    dfs = load_collections_to_dfs(mongo_uri=mongo_uri, db_name=db_name, fields_to_include = fields_to_include, batch_size= 1000, max_workers = 4)

    generate_all_figures(dfs)
    print("----------------------------------------------------------------------------------------")

    ################################################# PDF a email ######################################################################
    process_images_and_create_report()

    config = configparser.ConfigParser()
    config.read('config.ini')

    sender_email = config['email']['sender_email']
    sender_password = config['email']['sender_password']
    recipient_email = config['email']['recipient_email']
    subject = config['email']['subject']
    body = config['email']['body']
    file_path = config['email']['file_path']

    send_email_with_pdf(sender_email, sender_password, recipient_email, subject, body, file_path)