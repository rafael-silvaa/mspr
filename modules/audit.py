import socket
import json
import os
import csv
import ipaddress
import platform
import subprocess
import requests
from datetime import datetime
from .utils import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "configs", "audit.json")
LOGS_DIR = os.path.join(os.path.dirname(BASE_DIR), "logs")

# mapping API endoflife.date
API_MAPPING = {
    "Windows Server 2016": ("windows-server", "2016"),
    "Windows Server 2019": ("windows-server", "2019"),
    "Windows Server 2022": ("windows-server", "2022"),
    "Ubuntu 20.04 LTS": ("ubuntu", "20.04"),
    "CentOS 7": ("centos", "7"),
    "Windows 10": ("windows", "10"),
    "VMware ESXi 6.5": ("vmware-esxi", "6.5-6.7")
}

KNOWN_HOSTS = {
    "192.168.10.10": "Windows Server 2016", # DC01
    "192.168.10.11": "Windows Server 2016",
    "192.168.10.21": "Ubuntu 20.04 LTS",
    "192.168.10.22": "Ubuntu 20.04 LTS",
    "192.168.10.40": "CentOS 7",
    "192.168.10.50": "Windows Server 2019"
}

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

def fetch_eol_date_from_api(product, cycle):
    if ios_name not in API_MAPPING:
        return "INCONNU", "N/A"

    product, cycle = API_MAPPING[os_name]
    url = f"https://endoflife.date/api/v1/{product}.json"

    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            # cherche cycle correspondant (ex: 20.04)
            for entry in data:
                if entry['cycle'] == cycle:
                    eol_date = entry['eol']
                    
                    if isinstance(eol_date, str) and len(eol_date) == 10:
                        dt_eol = datetime.strptime(eol_date, "%Y-%m-%d")
                        if datetime.now() > dt_eol:
                            return "Obsolète", eol_date
                        else:
                            return "Supporté", eol_date
                    return "Supporté", str(eol_date)
    except Exception:
        return None
    return "Erreur API", "N/A"

def get_eol_status(os_name):
    """verif obsolescence via API"""
    if os_name not in API_MAPPING:
        return "INCONNU (Pas de mapping API)", "N/A"
    
    product_slug, cycle = API_MAPPING[os_name]
    
    # appel API
    eol_date_str = fetch_eol_date_from_api(product_slug, cycle)
    
    # fallback si API échoue (mode hors ligne ou API down)
    if not eol_date_str:
        return "ERREUR API (Vérifier Internet)", "N/A"

    # comparaison de date
    try:
        eol_date = datetime.strptime(eol_date_str, "%Y-%m-%d")
        today = datetime.now()
        
        if today > eol_date:
            return "OBSOLÈTE (DANGER)", eol_date_str
        else:
            return "SUPPORTÉ", eol_date_str
    except ValueError:
        return "ERREUR FORMAT DATE", eol_date_str

# def ping_host(ip):
#     """Ping une IP (Cross-platform)."""
#     param = '-n' if platform.system().lower() == 'windows' else '-c'
#     command = ['ping', param, '1', ip]
#     try:
#         return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
#     except Exception:
#         return False

# def scan_network(config):
#     print("\n--- AUDIT D'OBSOLESCENCE (Source: endoflife.date) ---")

#     config = load_config()
#     if not config:
#         print("Erreur de configuration audit.")
#         return

#     base_ip = config['network_range']
#     start = config['ip_start']
#     end = config['ip_end']
#     ports = config['ports_to_scan']
#     timeout = config['timeout']

#     print(f"\n[*] Audit du réseau {base_ip}{start}-{end}...")
#     print(f"[*] Ports ciblés : {ports}\n")

#     found_hosts = 0

#     # boucle sur les IPs
#     for i in range(start, end + 1):
#         ip = f"{base_ip}{i}"
        
#         open_ports = []
        
#         for port in ports:
#             sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             sock.settimeout(timeout)
#             result = sock.connect_ex((ip, port))
#             if result == 0:
#                 open_ports.append(port)
#             sock.close()

#         if open_ports:
#             found_hosts += 1
#             print(f"   [!] Hôte DÉCOUVERT : {ip} | Ports ouverts: {open_ports}")
#             # ici - logique obsolète ?
#             if 23 in open_ports: # telnet
#                 print(f"       /!\\ ALERTE : Telnet (Port 23) détecté ! Protocole obsolète.")
#             if 21 in open_ports: # FTP
#                 print(f"       /!\\ ALERTE : FTP (Port 21) détecté ! Non sécurisé.")

#     if found_hosts == 0:
#         print("\nAucune machine trouvée avec ces ports ouverts.")
#     else:
#         print(f"\nAudit terminé. {found_hosts} machines détectées.")

def scan_menu():
    while True:
        clear_screen()
        print("\n--- MODULE AUDIT & OBSOLESCENCE ---")
        print("1. Lancer le scan réseau")
        print("q. Retour")
        
        c = input("Choix : ")
        if c == '1':
            scan_network()
            wait_for_user()
        elif c == 'q':
            break
    
    # print(f"[*] Scan réseau : {subnet}")
    # audit_results = []

    # # scan rapide pour démo
    # for i in range(1, 60): 
    #     ip = f"{base_ip}.{i}"
        
    #     if ping_host(ip):
    #         detected_os = KNOWN_HOSTS.get(ip, "Inconnu")
            
    #         # message d'attente car l'API peut prendre quelques ms
    #         print(f"    [+] Machine trouvée : {ip} ({detected_os})... Vérification API...")
            
    #         status, date_eol = get_eol_status(detected_os)
            
    #         result_entry = {"ip": ip, "os": detected_os, "status": status, "eol_date": date_eol}
    #         audit_results.append(result_entry)
            
    #         print(f"        -> Résultat : {status} (Fin de vie : {date_eol})")

    # # generer CSV
    # if audit_results:
    #     filename = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    #     with open(filename, 'w', newline='', encoding='utf-8') as f:
    #         writer = csv.DictWriter(f, fieldnames=["ip", "os", "status", "eol_date"], delimiter=';')
    #         writer.writeheader()
    #         writer.writerows(audit_results)
    #     print(f"\n[SUCCÈS] Rapport CSV généré : {filename}")
    # else:
    #     print("\n[INFO] Aucune machine active détectée.")