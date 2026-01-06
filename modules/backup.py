import os
import subprocess
import mysql.connector
import csv
import paramiko
import json
from datetime import datetime
from .utils import *

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CURRENT_DIR, "configs", "backup.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"[ERREUR] Config introuvable : {CONFIG_FILE}")
        return None
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR] Lecture JSON : {e}")
        return None

def create_temp_dir():
    """crée un dossier avant """
    temp_dir = "backups_wms"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir

def transfer_to_nas(local_path, filename):
    """envoie fichier -> NAS + supprime copie locale si succès"""
    print(f"[*] Transfert de {filename} vers le NAS ({NAS_CONFIG['host']})...")
    
    try:
        # creer client SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # connect
        ssh.connect(
            NAS_CONFIG["host"], 
            username=NAS_CONFIG["user"], 
            password=NAS_CONFIG["password"]
        )
        
        sftp = ssh.open_sftp()
        
        # check dossier distant existant sinon creer
        try:
            sftp.chdir(NAS_CONFIG["remote_dir"])
        except IOError:
            print(f"[INFO] Le dossier distant n'existe pas, tentative de création...")
            sftp.mkdir(NAS_CONFIG["remote_dir"])
            sftp.chdir(NAS_CONFIG["remote_dir"])

        # envoi fichier
        remote_path = os.path.join(NAS_CONFIG["remote_dir"], filename)
        
        sftp.put(local_path, remote_path)
        sftp.close()
        ssh.close()
        
        print(f"[SUCCÈS] Fichier transféré sur le NAS : {remote_path}")
        
        # supp fichier local
        if os.path.exists(local_path):
            os.remove(local_path)
            print("[INFO] Copie locale supprimée.")
        return True

    except Exception as e:
        print(f"[ERREUR TRANSFERT] Impossible d'envoyer au NAS : {e}")
        print(f"[INFO] Le fichier est conservé localement ici : {local_path}")
        return False

def perform_sql_dump(config):
    """dump complet de la base via mysqldump"""
    db = config['database']
    tools = config['tools']
    nas = config['nas']
    
    print("\n[*] Démarrage de la sauvegarde SQL complète...")
    
    # crée fichier horodaté
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = create_temp_dir()
    filename = f"backup_{db}_{timestamp}.sql"
    local_path = os.path.join(temp_dir, filename) 

    command = [
        tools['mysqldump_path'],
        f"-h{db['host']}",
        f"-u{db['user']}",
        f"-p{db['password']}",
        db['db_name']
    ]

    # remove arg -p si pas de mdp
    if not db['password']:
        command.pop(3)

    try:
        # ouvrir le fichier as write pour verser le résultat de la commande
        with open(local_path, 'w') as outfile:
            subprocess.run(command, stdout=outfile, stderr=subprocess.PIPE, check=True, text=True)
        
        print(f"[SUCCÈS] Sauvegarde SQL générée: {local_path}")
        transfer_to_nas(local_path, filename)
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"[ERREUR] Échec de mysqldump. Code: {e.returncode}")
        print(f"Assurez-vous que 'mysqldump' est installé sur cette machine.")
        return False
    except FileNotFoundError:
        print("[ERREUR] Commande 'mysqldump' introuvable. Est-elle dans le PATH ?")
        return False

def export_table_csv(config):
    """exporte table spécifique en csv"""
    db = config['database']
    nas = config['nas']

    table_name = input("Quelle table voulez-vous exporter en CSV ? (users) : ")
    print(f"\n[*] Export de la table '{table_name}' en CSV...")
    
    try:
        conn = mysql.connector.connect(
            host=db['host'],
            user=db['user'],
            password=db["password"],
            database=db["db_name"]
        )
        cursor = conn.cursor()
        
        query = f"SELECT * FROM {table_name}"
        cursor.execute(query)
        
        # récupération des données et des en-têtes
        rows = cursor.fetchall()
        headers = [i[0] for i in cursor.description]
        
        # écriture du CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = create_temp_dir()
        filename = f"export_{table_name}_{timestamp}.csv"
        local_path = os.path.join(temp_dir, filename)
        
        with open(local_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(headers)
            writer.writerows(rows)
            
        print(f"[SUCCÈS] Export CSV généré : {filename} ({len(rows)} lignes)")
        
        cursor.close()
        conn.close()

        transfer_to_nas(local_path, filename, nas)
        return True

    except mysql.connector.Error as err:
        print(f"[ERREUR MySQL] {err}")
        return False

def run_backup_menu():
    """Sous-menu pour le module de sauvegarde."""
    config = load_config()
    if not config:
        print("\n[ERREUR CRITIQUE] Impossible de charger la configuration backup.")
        print("Vérifiez le fichier modules/configs/backup.json")
        wait_for_user() 
        return

    while True:
        clear_screen()

        print("\n--- MODULE SAUVEGARDE WMS ---")
        print("1. Sauvegarde complète (SQL Dump)")
        print("2. Export d'une table (CSV)")
        print("q. Retour au menu principal")
        
        choice = input("Choix : ")
        
        if choice == '1':
            perform_sql_dump(config)
            wait_for_user()
        elif choice == '2':
            export_table_csv(config)
            wait_for_user()
        elif choice == 'q':
            break
        else:
            print("Choix invalide.")