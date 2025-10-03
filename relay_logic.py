#!/usr/bin/env python3
import sqlite3
import time
from datetime import datetime, timedelta
from relay_manager import set_relay_status, read_relay_status

DB_PATH = '/home/kip/wally/sensor_data.db'

# Sensor-ID's
SENSOR_TANK_BOVEN = "28-0b24a0539bdb"
SENSOR_WARM_WATER = "28-0b24a050eaec"

# Relay-instellingen
RELAY_NUM = 1
SWITCH_INTERVAL = timedelta(minutes=5)  # Minimaal 5 minuten tussen schakelingen

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
    print("Start temperatuurgestuurde relaylogica...")
    
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

            current_status = read_relay_status(RELAY_NUM)

            if temp_water > 60.0:
                if current_status == 1:
                    print("Warm water boven 60°C → Relay UIT")
                    set_relay_status(RELAY_NUM, 0, "logic_warm_water")
                else:
                    print("Warm water boven 60°C → Relay al uit")
            elif temp_tank > 70.0:
                if current_status == 0:
                    print("Tank boven 70°C → Relay AAN")
                    set_relay_status(RELAY_NUM, 1, "logic_tank_hoog")
                else:
                    print("Tank boven 70°C → Relay al aan")
            else:
                print("Geen actie nodig")

            time.sleep(60)

        except KeyboardInterrupt:
            print("Gestopt.")
            break
        except Exception as e:
            print(f"Fout: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
