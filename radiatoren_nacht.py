#!/usr/bin/env python3
import sqlite3
import time
import requests
from datetime import datetime, timedelta

DB_PATH = '/home/kip/wally/sensor_data.db'
API_BASE = "http://localhost"

# Relay-instellingen
RELAY_RADIATOREN = 2  # Relay voor radiatoren
DAG_START = 6         # 06:00 - Relay AAN
NACHT_START = 20      # 20:00 - Start cyclus
NACHT_EIND = 6        # 06:00 - Einde cyclus
AAN_TIJD = 10         # 10 minuten aan
UIT_TIJD = 50         # 50 minuten uit

def get_relay_status_via_api(relay_num):
    """Lees relay status via web_interface API"""
    try:
        response = requests.get(f"{API_BASE}/api/relay_status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get(str(relay_num), {}).get('status')
    except Exception as e:
        print(f"API fout: {e}")
    return None

def set_relay_via_api(relay_num, status, reason=""):
    """Schakel relay via web_interface API"""
    try:
        url = f"{API_BASE}/relay/{relay_num}/{1 if status else 0}"
        response = requests.get(url, timeout=5)
        success = response.status_code == 200
        if success:
            status_tekst = "AAN" if status else "UIT"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Radiatoren relay {status_tekst} - {reason}")
        return success
    except Exception as e:
        print(f"API set fout: {e}")
    return False

def is_dag_mode():
    """Check of we in dagperiode zitten (06:00 - 22:00)"""
    now = datetime.now()
    current_hour = now.hour
    
    # Dag van 06:00 tot 22:00
    if DAG_START <= current_hour < NACHT_START:
        return True
    return False

def is_nacht_mode():
    """Check of we in nachtperiode zitten (22:00 - 06:00)"""
    now = datetime.now()
    current_hour = now.hour
    
    # Nacht van 22:00 tot 06:00
    if current_hour >= NACHT_START or current_hour < DAG_START:
        return True
    return False

def get_nacht_cycle_status():
    """Bepaal of relay AAN of UIT moet zijn gebaseerd op tijd in nachtperiode"""
    now = datetime.now()
    
    # Tijd sinds middernacht in minuten
    total_minutes = now.hour * 60 + now.minute
    
    # Als na middernacht maar voor 06:00, tel 24 uur op voor berekening
    if now.hour < DAG_START:
        total_minutes += 24 * 60
    
    # Start nacht om 22:00 = 1320 minuten
    nacht_start_minutes = NACHT_START * 60
    tijd_in_nacht = total_minutes - nacht_start_minutes
    
    # Bepaal positie in cyclus (60 minuten cyclus)
    positie_in_cyclus = tijd_in_nacht % (AAN_TIJD + UIT_TIJD)
    
    # Eerste AAN_TIJD minuten = AAN, daarna UIT_TIJD minuten = UIT
    if positie_in_cyclus < AAN_TIJD:
        return True  # AAN
    else:
        return False  # UIT

def main():
    print("Start radiatoren dag/nacht cyclus (API mode)...")
    print(f"Dag (AAN): {DAG_START:02d}:00 - {NACHT_START:02d}:00")
    print(f"Nacht (cyclus): {NACHT_START:02d}:00 - {DAG_START:02d}:00")
    print(f"Nacht cyclus: {AAN_TIJD}min AAN, {UIT_TIJD}min UIT")
    
    laatste_modus = None  # 'dag' of 'nacht'
    laatste_cyclus_status = None
    
    while True:
        try:
            now = datetime.now()
            
            # LEES RELAY STATUS VIA API
            huidige_relay_status = get_relay_status_via_api(RELAY_RADIATOREN)
            
            if huidige_relay_status is None:
                print(f"[{now.strftime('%H:%M:%S')}] Kon relay status niet lezen via API")
                time.sleep(60)
                continue
            
            if is_dag_mode():
                # DAG MODE - relay altijd AAN
                if laatste_modus != 'dag':
                    print(f"[{now.strftime('%H:%M:%S')}] 🟢 Dag mode - Zet relay AAN")
                    set_relay_via_api(RELAY_RADIATOREN, 1, "dag_mode_aan")
                    laatste_modus = 'dag'
                    laatste_cyclus_status = None
                elif not huidige_relay_status:
                    # Relay is per ongeluk uit, zet weer aan
                    set_relay_via_api(RELAY_RADIATOREN, 1, "dag_mode_herstel")
                
                # Status log elke 10 minuten om spam te voorkomen
                if now.minute % 10 == 0:
                    print(f"[{now.strftime('%H:%M:%S')}] Dag - Relay AAN")
                    
            elif is_nacht_mode():
                # NACHT MODE - volg 10min/50min cyclus
                if laatste_modus != 'nacht':
                    print(f"[{now.strftime('%H:%M:%S')}] 🔵 Nacht mode - Start cyclus")
                    laatste_modus = 'nacht'
                
                gewenste_status = get_nacht_cycle_status()
                
                if gewenste_status is not None and gewenste_status != laatste_cyclus_status:
                    if gewenste_status:
                        set_relay_via_api(RELAY_RADIATOREN, 1, "nacht_cyclus_aan")
                    else:
                        set_relay_via_api(RELAY_RADIATOREN, 0, "nacht_cyclus_uit")
                    laatste_cyclus_status = gewenste_status
                
                # Toon huidige status elke cyclus wissel
                if now.minute % 5 == 0:  # Elke 5 minuten loggen
                    status_tekst = "AAN" if huidige_relay_status else "UIT"
                    cyclus_tekst = "AAN fase" if get_nacht_cycle_status() else "UIT fase"
                    print(f"[{now.strftime('%H:%M:%S')}] Nacht - Relay: {status_tekst} ({cyclus_tekst})")
            
            time.sleep(60)  # Check elke minuut
            
        except KeyboardInterrupt:
            print("Gestopt.")
            break
        except Exception as e:
            print(f"Fout: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()