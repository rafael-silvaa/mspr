import sys
import json
import os
from modules import diagnostic, backup, audit
from modules.utils import *

def main_menu():
    while True: 
        clear_screen()

        print("\n" + "="*30)
        print("   NTL-SysToolBox - MENU")
        print("="*30)
        print("1. Module Diagnostic (Santé Réseau)")
        print("2. Module Sauvegarde (WMS & NAS)")
        print("3. Module Audit (Obsolescence)")
        print("q. Quitter")

        choice = input("Votre choix: ")

        if choice == '1':
            clear_screen()
            
            print("Lancement du diagnostic...")
            diagnostic.run_diagnostic()
            wait_for_user()

        elif choice == '2':
            backup.run_backup_menu() 

        elif choice == '3':
            print("Lancement de l'audit...")
            audit.scan_menu()

        elif choice == 'q':
            print("Fermeture")
            sys.exit(0)

        else:
            print("Choix invalide.")

if __name__ == "__main__":
    main_menu()
