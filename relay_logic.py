#!/usr/bin/env python3
import sqlite3
import time
import requests
from datetime import datetime, timedelta

DB_PATH = '/home/kip/wally/sensor_data.db'
API_BASE = "http://localhost"

# Sensor-ID's
SENSOR_TANK_BOVEN = "28-0b24a0539bdb"
SENSOR_WARM_WATER = "28-0b24a050eaec"

# Relay-instellingen
RELAY_NUM = 1
SWITCH_INTERVAL = timedelta(minutes=5)

# HYSTERESIS INSTELLINGEN
TEMP_WATER_AAN = 58.0   # Relay AAN als water < 58°C
TEMP_WATER_UIT = 60.0   # Relay UIT als water > 60°C
TEMP_TANK_AAN = 70.0    # Relay AAN als tank > 70°C (noodscenario)

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

def set_relay_via_api(relay_num, status):
    """Schakel relay via web_interface API"""
    try:
        url = f"{API_BASE}/relay/{relay_num}/{1 if status else 0}"
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"API set fout: {e}")
    return False

def get_latest_temp(sensor_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT temperature, timestamp
        FROM sensor_readings
        WHERE sensor_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (sensor_id,))
    row = c.fetchone()
    conn.close()
    if row:
        temp, ts = row
        return temp, datetime.fromisoformat(ts)
    return None, None

def get_last_relay_switch_time(relay_num):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT timestamp
        FROM relay_status
        WHERE relay_number = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (relay_num,))
    row = c.fetchone()
    conn.close()
    if row:
        return datetime.fromisoformat(row[0])
    return None

def main():
    print("Start temperatuurgestuurde relaylogica (API mode)...")
    print(f"Water: UIT > {TEMP_WATER_UIT}°C")
    print(f"AAN alleen als: Water < {TEMP_WATER_AAN}°C EN Tank > {TEMP_TANK_AAN}°C")
    
    while True:
        try:
            temp_tank, ts1 = get_latest_temp(SENSOR_TANK_BOVEN)
            temp_water, ts2 = get_latest_temp(SENSOR_WARM_WATER)
            now = datetime.now()

            if temp_tank is None or temp_water is None:
                print("Geen temperatuurdatas beschikbaar.")
                time.sleep(60)
                continue

            print(f"[{now.strftime('%H:%M:%S')}] Tank: {temp_tank:.1f}°C, Warm water: {temp_water:.1f}°C")

            last_switch = get_last_relay_switch_time(RELAY_NUM)
            if last_switch and now - last_switch < SWITCH_INTERVAL:
                print(f"Relay {RELAY_NUM} laatst geschakeld op {last_switch}, wacht nog even.")
                time.sleep(60)
                continue

            # LEES VIA API
            current_status = get_relay_status_via_api(RELAY_NUM)
            print(f"Relay status via API: {current_status}")

            if current_status is None:
                print("Kon relay status niet lezen via API")
                time.sleep(60)
                continue

            # LOGICA
            action_taken = False
            
            # 1. PRIORITEIT: Water te warm (UIT)
            if temp_water > TEMP_WATER_UIT:
                if current_status == 1:
                    print(f"Warm water boven {TEMP_WATER_UIT}°C → Relay UIT")
                    set_relay_via_api(RELAY_NUM, 0)
                else:
                    print(f"Warm water boven {TEMP_WATER_UIT}°C → Relay al uit")
                action_taken = True
                
            # 2. PRIORITEIT: Water te koud EN Tank warm genoeg (AAN)
            elif temp_water < TEMP_WATER_AAN and temp_tank > TEMP_TANK_AAN:
                if current_status == 0:
                    print(f"Warm water onder {TEMP_WATER_AAN}°C EN Tank boven {TEMP_TANK_AAN}°C → Relay AAN")
                    set_relay_via_api(RELAY_NUM, 1)
                else:
                    print(f"Warm water onder {TEMP_WATER_AAN}°C EN Tank boven {TEMP_TANK_AAN}°C → Relay al aan")
                action_taken = True
                
            if not action_taken:
                # Geen actie nodig
                if temp_water < TEMP_WATER_AAN:
                    print(f"Water te koud ({temp_water:.1f}°C) maar tank niet warm genoeg ({temp_tank:.1f}°C)")
                else:
                    print(f"Geen actie nodig (water: {temp_water:.1f}°C)")

            time.sleep(60)

        except KeyboardInterrupt:
            print("Gestopt.")
            break
        except Exception as e:
            print(f"Fout: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()