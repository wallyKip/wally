#!/usr/bin/env python3
import sqlite3
import time
from datetime import datetime
from relay_manager import read_relay_status_oneshot

DB_PATH = '/home/kip/wally/sensor_data.db'

SENSOR_MAPPING = {
    "28-0b24a04fc39f": "A - Naar radiatoren",
    "28-0b24a0539bdb": "B - Grote tank boven",
    "28-0b24a0545ad2": "C - Grote tank midden",
    "28-0b24a0507904": "D - Grote tank onder",
    "28-0b24a0569043": "E - Wally uitgang",
    "28-0b24a050eaec": "F - Warm water",
    "28-0b24a03a4d26": "G - Warm water ingang",
    "28-0b24a0551b3c": "H - Warm water uitgang"
}

def read_sensor_temperature(sensor_id):
    """Lees temperatuur van een specifieke sensor"""
    sensor_path = f"/sys/bus/w1/devices/{sensor_id}/w1_slave"
    try:
        with open(sensor_path, 'r') as f:
            content = f.read()
            if 'YES' in content:
                temp_line = content.split('t=')[-1]
                return float(temp_line) / 1000.0
    except:
        return None
    return None

def save_temperature(sensor_id, temperature):
    """Sla temperatuurmeting op in de database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO sensor_readings (sensor_id, temperature) VALUES (?, ?)",
        (sensor_id, temperature)
    )
    conn.commit()
    conn.close()

def log_relay_status():
    """Lees status van relais via relay_manager en sla op in database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for relay_num in [1, 2]:
        try:
            status = read_relay_status_oneshot(relay_num)
            c.execute('''
                INSERT INTO relay_status (relay_number, status, reason)
                VALUES (?, ?, ?)
            ''', (relay_num, status, "data_collector"))
            print(f"  Relay {relay_num}: {'AAN' if status else 'UIT'}")
        except Exception as e:
            print(f"  Relay {relay_num}: FOUT ({e})")

    conn.commit()
    conn.close()

def collect_data():
    """Verzamel data van sensoren en relais"""
    print(f"{datetime.now()} - Data verzamelen...")

    for sensor_id, sensor_name in SENSOR_MAPPING.items():
        temp = read_sensor_temperature(sensor_id)
        if temp is not None:
            save_temperature(sensor_id, temp)
            print(f"  {sensor_name}: {temp:.1f}°C")
        else:
            print(f"  {sensor_name}: ERROR")

    # Log relay status
    log_relay_status()

def main():
    print("Sensor Logger gestart. Druk op Ctrl+C om te stoppen.")
    while True:
        try:
            collect_data()
            time.sleep(60)  # Elke minuut
        except KeyboardInterrupt:
            print("\nGestopt door gebruiker.")
            break
        except Exception as e:
            print(f"Fout: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()
