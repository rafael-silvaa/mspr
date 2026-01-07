import os
import psutil
import platform
import time
import socket
import paramiko
import json
from datetime import datetime
from .utils import *

BASE_DIR = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "configs", "diagnostic.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

def load_inventory():
    """"load config depuis json"""
    if not os.path.exists(CONFIG_FILE):
        print(f"[ERREUR] Le fichier de configuration est introuvable : {CONFIG_FILE}")
        return {}
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERREUR] Le fichier JSON est mal formaté : {e}")
        return {}

def save_report_json(machine_name, data):
    """exporter le dic de données -> JSON"""
    if not os.path.exists(LOGS_DIR):
        try:
            os.makedirs(LOGS_DIR)
        except OSError as e:
            print(f"[ERREUR] Impossible de créer le dossier logs : {e}")
            return

    safe_name = "".join([c if c.isalnum() else "_" for c in machine_name])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"diag_{safe_name}_{timestamp}.json"
    filepath = os.path.join(LOGS_DIR, filename)

    full_report = {
        "machine": machine_name,
        "scan_date": datetime.now().isoformat(),
        "scan_result": data
    }

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, indent=4, ensure_ascii=False)
        print(f"\n[SUCCÈS] Rapport exporté ici : {filepath}")
    except Exception as e:
        print(f"\n[ERREUR] Échec de l'export JSON : {e}")

def get_remote_linux_health(ip, user, password):
    """connecte SSH + commandes Linux pour récup l'état"""
    print(f"[*] Connexion SSH vers {ip}...")
    info = {}
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(ip, username=user, password=password, timeout=5)
        
        # 1. récup OS
        stdin, stdout, stderr = client.exec_command("cat /etc/os-release | grep PRETTY_NAME")
        os_name = stdout.read().decode().strip().replace('PRETTY_NAME=', '').replace('"', '')
        info['OS'] = os_name if os_name else "Linux inconnu"

        # 2. récup uptime
        stdin, stdout, stderr = client.exec_command("uptime -p")
        info['Uptime'] = stdout.read().decode().strip()

        # 3. récup CPU load
        stdin, stdout, stderr = client.exec_command("cat /proc/loadavg")
        load = stdout.read().decode().split()[0]
        info['CPU Load'] = f"{load} (Load Avg)"

        # 4. récup RAM (libre/total)
        cmd_ram = "free -m | awk 'NR==2{printf \"%.2f\", $3*100/$2 }'"
        stdin, stdout, stderr = client.exec_command(cmd_ram)
        info['RAM'] = f"{stdout.read().decode().strip()}% utilisée"

        # 5. récup disque
        cmd_disk = "df -h / | awk 'NR==2 {print $5}'"
        stdin, stdout, stderr = client.exec_command(cmd_disk)
        info['Disque'] = stdout.read().decode().strip()

        client.close()
        return info

    except Exception as e:
        return {"ERREUR": f"Connexion impossible ou échec commandes: {e}"}

def check_simple_ports(ip, ports):
    """pour machines Windows sans SSH, vérifier juste les ports"""
    print(f"[*] Scan réseau vers {ip} (Mode limité)...")
    info = {"OS": "Windows (Probable)", "Type": "Scan de Ports (Pas d'accès WMI/SSH)"}
    
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((ip, port))
        status = "OUVERT" if result == 0 else "FERMÉ"
        info[f"Port {port}"] = status
        sock.close()
    
    # try ping basique 
    try:
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', ip]
        response = psutil.subprocess.call(command, stdout=psutil.subprocess.DEVNULL, stderr=psutil.subprocess.DEVNULL)
        info["Ping"] = "OK" if response == 0 else "TimeOut"
    except Exception:
            info["Ping"] = "Erreur commande ping"
    
    return info

def display_report(machine_name, data):
    """Afficher résultats"""
    if not data:
        print(f"\n[!] Aucun résultat ou erreur lors du scan de {machine_name}.")
        return

    print("\n" + "="*40)
    print(f" RAPPORT : {machine_name}")
    print("="*40)
    for key, value in data.items():
        print(f" {key:<15} : {value}")
    print("="*40 + "\n")

def run_diagnostic():
    inventory = load_inventory()

    if not inventory:
        print("Aucune configuration chargée. Vérifiez configs/diagnostic.json")
        return

    while True:
        # clear_screen()

        print("\n--- MENU DIAGNOSTIC RÉSEAU ---")
        print("Sélectionnez la machine à scanner :")
        
        keys = sorted(inventory.keys())
        for key in keys:
            val = inventory[key]
            print(f"{key}. {val['name']} ({val['ip']})")
        
        print("q. Quitter")
        
        choice = input("\nVotre choix : ")
        
        if choice == 'q':
            break
            
        if choice in inventory:
            target = inventory[choice]
            data = {}
            
            print(f"[*] Détection de l'OS de {target['ip']}...")
            detected_type = detect_os_type(target['ip'])
            
            current_type = target['type']
            if target['type'] != 'local' and detected_type != 'unknown':
                current_type = detected_type
                print(f"    -> OS Détecté : {current_type}")
            
            # scan
            try:
                if current_type == "local":
                    # analyse locale (psutil)
                    data = get_local_health()
                    
                elif current_type == "linux_ssh":
                    # analyse distante Linux (SSH)
                    # user/pass necessaire
                    data = get_remote_linux_health(target["ip"], target.get("user"), target.get("password"))
                    
                elif current_type == "windows_remote":
                    # win detected -> scan ports
                    data = check_simple_ports(target["ip"], [135, 445, 3389])
                
                display_report(target["name"], data)

                save = input("Voulez-vous exporter ce rapport en JSON? (y/N) : ")
                if save.lower() == 'y':
                    save_report_json(target["name"], data)
                
                wait_for_user()
                    
            except Exception as e:
                print(f"\n/!\ Une erreur est survenue pendant le scan :")
                print(f"{e}")
                print("Vérifiez vos IPs, mots de passe et connexions.")
                wait_for_user()
        else:
            print("Choix invalide.")

if __name__ == "__main__":
    try:
        run_diagnostic()
    except KeyboardInterrupt:
        print("\nArrêt forcé.")