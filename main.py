import sys
import json
import os
from modules import diagnostic, backup, audit

def load_config():
    # logique pour verif var env
    with open('config.json', 'r') as f:
        return json.load(f)

def main_menu():
    config = load_config()

    while True: 
        print("\n--- NTL-SysToolBox ---")
        print("1. Module Diagnostic (Santé)")
        print("2. Module Sauvegarde (WMS)")
        print("3. Module Audit (Obsolescence)")
        print("q. Quitter")

        choice = input("Votre choix: ")

        if choice == '1':
            print("Lancement du diagnostic...")
            diagnostic.run_diagnostic()
            input("\nAppuyez sur Entrée pour revenir au menu:")
        elif choice == '2':
            backup.run_backup_menu(config) 
        elif choice == '3':
            print("Lancement de l'audit...")
            audit.scan_network(config)
        elif choice == 'q':
            print("Fermeture")
            sys.exit(0)
        else:
            print("Choix invalide.")

if __name__ == "__main__":
    main_menu()
