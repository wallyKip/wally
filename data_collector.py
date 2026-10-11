#!/usr/bin/env python3
import sqlite3
import time
from datetime import datetime
from relay_manager import read_relay_status

DB_PATH = '/home/kip/wally/sensor_data.db'

# Alleen de 3 sensoren van de grote tank
BIG_TANK_SENSORS = {
    "28-0b24a0539bdb": "B - Grote tank boven",
    "28-0b24a0545ad2": "C - Grote tank midden",
    "28-0b24a0507904": "D - Grote tank onder",
}

def read_sensor_temperature(sensor_id):
    """Lees temperatuur van een specifieke sensor (1 decimaal)"""
    sensor_path = f"/sys/bus/w1/devices/{sensor_id}/w1_slave"
    try:
        with open(sensor_path, 'r') as f:
            content = f.read()
            if 'YES' in content:
                temp_line = content.split('t=')[-1]
                temp = float(temp_line) / 1000.0
                return round(temp, 1)
    except:
        return None
    return None

def save_temperatures_batch(readings):
    """Sla meerdere sensormetingen op met hetzelfde timestamp."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for sensor_id, temperature in readings:
        c.execute(
            "INSERT INTO sensor_readings (sensor_id, temperature, timestamp) VALUES (?, ?, ?)",
            (sensor_id, temperature, now)
        )
    conn.commit()
    conn.close()

def log_relay_status():
    """Lees status van relais en sla op in zowel relay_status als current_relay_status."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for relay_num in [1, 2]:
        try:
            status = read_relay_status(relay_num)
            status_int = 1 if status else 0

            # historische log
            c.execute('''
                INSERT INTO relay_status (relay_number, status, reason)
                VALUES (?, ?, ?)
            ''', (relay_num, status_int, "data_collector"))

            # actuele status (voor web interface)
            c.execute('''
                INSERT OR REPLACE INTO current_relay_status (relay_number, status, last_updated)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (relay_num, status_int))

            print(f"  Relay {relay_num}: {'AAN' if status else 'UIT'}")
        except Exception as e:
            print(f"  Relay {relay_num}: FOUT ({e})")

    conn.commit()
    conn.close()

def collect_data():
    """Verzamel data van de 3 grote-tank sensoren + relay status"""
    print(f"{datetime.now()} - Data verzamelen...")

    # Sensoren
    readings = []
    for sensor_id, sensor_name in BIG_TANK_SENSORS.items():
        temp = read_sensor_temperature(sensor_id)
        if temp is not None:
            readings.append((sensor_id, temp))
            print(f"  {sensor_name}: {temp:.1f}°C")
        else:
            print(f"  {sensor_name}: ERROR")

    if len(readings) == len(BIG_TANK_SENSORS):
        save_temperatures_batch(readings)
        print(f"  → {len(readings)} metingen opgeslagen met timestamp {datetime.now().strftime('%H:%M:%S')}")
    else:
        print(f"  → Onvolledige meting ({len(readings)}/{len(BIG_TANK_SENSORS)}), niet opgeslagen")

    # Relais
    log_relay_status()

def main():
    print("Sensor Logger gestart (grote tank + relais). Druk op Ctrl+C om te stoppen.")
    while True:
        try:
            collect_data()
            time.sleep(300)  # elke 5 minuten
        except KeyboardInterrupt:
            print("\nGestopt door gebruiker.")
            break
        except Exception as e:
            print(f"Fout: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()