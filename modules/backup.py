import os
import subprocess
import mysql.connector
import csv
from datetime import datetime

def create_backup_dir():
    """crée dossier backups si pas existant"""
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    return backup_dir

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
    filename = os.path.join(backup_dir, f"backup_{db_name}_{timestamp}.sql")

    # construction commande système mysqldump
    # Note : mysqldump doit être installé et accessible dans le PATH du système
    command = [
        "mysqldump",
        f"-h{host}",
        f"-u{user}",
        f"-p{password}",
        db_name
    ]

    try:
        # ouvrir le fichier as write pour verser le résultat de la commande
        with open(filename, 'w') as outfile:
            subprocess.run(command, stdout=outfile, stderr=subprocess.PIPE, check=True, text=True)
        
        print(f"    [SUCCÈS] Sauvegarde SQL générée : {filename}")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"    [ERREUR] Échec de mysqldump. Code: {e.returncode}")
        print(f"    Assurez-vous que 'mysqldump' est installé sur cette machine.")
        return False
    except FileNotFoundError:
        print("    [ERREUR] Commande 'mysqldump' introuvable. Est-elle dans le PATH ?")
        return False

def export_table_csv(config):
    """Exporte une table spécifique en CSV."""
    table_name = input("Quelle table voulez-vous exporter en CSV ? (ex: users) : ")
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
        backup_dir = create_backup_dir()
        filename = os.path.join(backup_dir, f"export_{table_name}_{timestamp}.csv")
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(headers)
            writer.writerows(rows)
            
        print(f"    [SUCCÈS] Export CSV généré : {filename} ({len(rows)} lignes)")
        
        cursor.close()
        conn.close()
        return True

    except mysql.connector.Error as err:
        print(f"    [ERREUR MySQL] {err}")
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