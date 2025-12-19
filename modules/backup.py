import os
import subprocess
import mysql.connector
import csv
import paramiko
from datetime import datetime

NAS_CONFIG = {
    "host": "192.168.1.132",
    "user": "nas",
    "password": "admin",
    "remote_dir": "/srv/ntl_data/"
}

def create_temp_dir():
    """crée un dossier avant """
    temp_dir = "backups_wms"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir

def create_backup_dir():
    """crée dossier backups si pas existant"""
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    return backup_dir

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
        os.remove(local_path)
        print("[INFO] Copie locale supprimée.")
        return True

    except Exception as e:
        print(f"[ERREUR TRANSFERT] Impossible d'envoyer au NAS : {e}")
        print(f"[INFO] Le fichier est conservé localement ici : {local_path}")
        return False

def perform_sql_dump(config):
    """dump complet de la base via mysqldump"""
    print("\n[*] Démarrage de la sauvegarde SQL complète...")
    
    db_conf = config.get("database", {})
    host = db_conf.get("host", "localhost")
    user = db_conf.get("user", "root")
    password = db_conf.get("password", "")
    db_name = db_conf.get("db_name", "wms_prod")
    
    # crée fichier horodaté
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = create_backup_dir()
    temp_dir = create_temp_dir()
    filename_only = f"backup_{db_name}_{timestamp}.sql"
    full_local_path = os.path.join(temp_dir, filename_only) 

    # commande système mysqldump
    path_to_tool = r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe"

    command = [
        path_to_tool,
        f"-h{host}",
        f"-u{user}",
        f"-p{password}",
        db_name
    ]

    try:
        # ouvrir le fichier as write pour verser le résultat de la commande
        with open(full_local_path, 'w') as outfile:
            subprocess.run(command, stdout=outfile, stderr=subprocess.PIPE, check=True, text=True)
        
        print(f"[SUCCÈS] Sauvegarde SQL générée: {full_local_path}")

        transfer_to_nas(full_local_path, filename_only)
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
    table_name = input("Quelle table voulez-vous exporter en CSV ? (users) : ")
    print(f"\n[*] Export de la table '{table_name}' en CSV...")

    db_conf = config.get("database", {})
    
    try:
        conn = mysql.connector.connect(
            host=db_conf.get("host"),
            user=db_conf.get("user"),
            password=db_conf.get("password"),
            database=db_conf.get("db_name")
        )
        cursor = conn.cursor()
        
        query = f"SELECT * FROM {table_name}"
        cursor.execute(query)
        
        # récupération des données et des en-têtes
        rows = cursor.fetchall()
        headers = [i[0] for i in cursor.description]
        
        # écriture du CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = create_temp_dir()
        filename_only = f"export_{table_name}_{timestamp}.csv"
        full_local_path = os.path.join(temp_dir, filename_only)
        
        with open(full_local_path, 'w', newline='', encoding='utf-32') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(headers)
            writer.writerows(rows)
            
        print(f"[SUCCÈS] Export CSV généré : {filename} ({len(rows)} lignes)")
        
        cursor.close()
        conn.close()

        transfer_to_nas(full_local_path, filename_only)
        return True

    except mysql.connector.Error as err:
        print(f"[ERREUR MySQL] {err}")
        return False

def run_backup_menu(config):
    """Sous-menu pour le module de sauvegarde."""
    while True:
        print("\n--- MODULE SAUVEGARDE WMS ---")
        print("1. Sauvegarde complète (SQL Dump)")
        print("2. Export d'une table (CSV)")
        print("q. Retour au menu principal")
        
        choice = input("Choix : ")
        
        if choice == '1':
            perform_sql_dump(config)
        elif choice == '2':
            export_table_csv(config)
        elif choice == 'q':
            break
        else:
            print("Choix invalide.")