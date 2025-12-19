import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def wait_for_user():
    input("\nAppuyez sur Entrée pour continuer...")