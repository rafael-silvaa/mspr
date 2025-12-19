import platform
import subprocess
import csv
import requests
from datetime import datetime

# mapping API endoflife.date
API_MAPPING = {
    "Windows Server 2016": ("windows-server", "2016"),
    "Windows Server 2019": ("windows-server", "2019"),
    "Ubuntu 20.04 LTS": ("ubuntu", "20.04"),
    "CentOS 7": ("centos", "7"),
    "Windows 10": ("windows", "10"),
    "ESXi 6.5": ("vmware-esxi", "6.5")
}

KNOWN_HOSTS = {
    "192.168.10.10": "Windows Server 2016",
    "192.168.10.11": "Windows Server 2016",
    "192.168.10.21": "Ubuntu 20.04 LTS",
    "192.168.10.22": "Ubuntu 20.04 LTS",
    "192.168.10.40": "CentOS 7",
    "192.168.10.50": "Windows Server 2019"
}

def fetch_eol_date_from_api(product, cycle):
    url = f"https://endoflife.date/api/{product}.json"
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            # cherche cycle correspondant (ex: 20.04)
            for entry in data:
                if entry['cycle'] == cycle:
                    return entry['eol'] # format YYYY-MM-DD
    except Exception:
        return None
    return None

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

def ping_host(ip):
    """Ping une IP (Cross-platform)."""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', ip]
    try:
        return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    except Exception:
        return False

def scan_network(config):
    print("\n--- AUDIT D'OBSOLESCENCE (Source: endoflife.date) ---")
    
    subnet = config.get("network", {}).get("target_subnet", "192.168.10.0/24")
    base_ip = ".".join(subnet.split('.')[:3])
    
    print(f"[*] Scan réseau : {subnet}")
    audit_results = []

    # scan rapide pour démo
    for i in range(1, 60): 
        ip = f"{base_ip}.{i}"
        
        if ping_host(ip):
            detected_os = KNOWN_HOSTS.get(ip, "Inconnu")
            
            # message d'attente car l'API peut prendre quelques ms
            print(f"    [+] Machine trouvée : {ip} ({detected_os})... Vérification API...")
            
            status, date_eol = get_eol_status(detected_os)
            
            result_entry = {"ip": ip, "os": detected_os, "status": status, "eol_date": date_eol}
            audit_results.append(result_entry)
            
            print(f"        -> Résultat : {status} (Fin de vie : {date_eol})")

    # generer CSV
    if audit_results:
        filename = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["ip", "os", "status", "eol_date"], delimiter=';')
            writer.writeheader()
            writer.writerows(audit_results)
        print(f"\n[SUCCÈS] Rapport CSV généré : {filename}")
    else:
        print("\n[INFO] Aucune machine active détectée.")