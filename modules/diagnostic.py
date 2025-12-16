import psutil
import platform
import time
import socket
import json
from datetime import datetime

def get_system_health():
    """Récupère les informations de santé de la machine locale (Windows ou Linux)."""

    # infos OS & uptime
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    uptime = datetime.now() - bt

    system_info = {
        "os_type": platform.system(),
        "os_release": platform.release(),
        "hostname": platform.node(),
        "uptime_str": str(uptime).split('.')[0], # enleve les microsecondes
        "cpu_usage_percent": psutil.cpu_percent(interval=1),
        "ram_usage_percent": psutil.virtual_memory().percent,
        "disk_usage_percent": psutil.disk_usage('/').percent
    }
    return system_info

def check_remote_port(ip, port, service_name):
    """Teste si un port est ouvert sur une machine distante (Test basique de service)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2) # timeout court pour ne pas bloquer
    result = sock.connect_ex((ip, port))
    sock.close()

    status = "OK" if result == 0 else "ERREUR/INACCESSIBLE"
    return {"service": service_name, "target": ip, "port": port, "status": status}

def run_diagnostic(config):
    """Fonction principale du module."""
    print("\n--- DIAGNOSTIC SYSTÈME ---")
    
    # A. santé locale
    print(f"[*] Analyse de la machine locale...")
    local_health = get_system_health()
    
    # affichage humain
    print(f"    OS: {local_health['os_type']} {local_health['os_release']}")
    print(f"    Uptime: {local_health['uptime_str']}")
    print(f"    CPU: {local_health['cpu_usage_percent']}% | RAM: {local_health['ram_usage_percent']}% | Disque: {local_health['disk_usage_percent']}%")

    # B. verification des services critiques (AD, DNS, MySQL)
    # IPs recuperes depuis la config (annexe C)
    print(f"\n[*] Vérification des services critiques distants...")
    
    targets = [
        ("192.168.10.10", 53, "DNS (DC01)"),      # Port DNS
        ("192.168.10.10", 389, "AD (DC01)"),      # Port LDAP
        ("192.168.10.21", 3306, "MySQL (WMS-DB)") # Port MySQL
    ]
    
    services_status = []
    for ip, port, name in targets:
        res = check_remote_port(ip, port, name)
        services_status.append(res)
        print(f"    {name} sur {ip}:{port} -> {res['status']}")

    # C. generer du rapport json
    full_report = {
        "timestamp": datetime.now().isoformat(),
        "local_health": local_health,
        "remote_services": services_status
    }

    # sauvegarder ou afficher json
    # sauvegarder dans un dossier de logs (?)
    json_output = json.dumps(full_report, indent=4)
    # print("\n[DEBUG] Sortie JSON générée (interne)")
    return full_report