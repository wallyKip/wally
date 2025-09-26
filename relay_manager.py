#!/usr/bin/env python3
import sqlite3
import time
import gpiod
from datetime import datetime

DB_PATH = '/home/pi/wally/sensor_data.db'
RELAY_GPIO_PINS = {1: 5, 2: 6}  # relay_number: BCM GPIO pin
CHIP_NAME = 'gpiochip0'

# Initialiseer GPIO
chip = gpiod.Chip(CHIP_NAME)
relay_lines = {
    relay_num: chip.get_line(gpio_pin)
    for relay_num, gpio_pin in RELAY_GPIO_PINS.items()
}
for line in relay_lines.values():
    line.request(consumer="relay_manager", type=gpiod.LINE_REQ_DIR_OUT)

def read_relay_status(relay_number):
    """Lees huidige status van een relay via GPIO"""
    line = relay_lines.get(relay_number)
    if not line:
        return None
    return line.get_value()

def set_relay_status(relay_number, status, reason="manual"):
    """Zet relay status en sla op in database"""
    line = relay_lines.get(relay_number)
    if not line:
        print(f"Relay {relay_number} niet gevonden.")
        return False

    try:
        # Zet GPIO waarde
        line.set_value(1 if status else 0)

        # Sla op in database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Update current status
        c.execute('''
            INSERT OR REPLACE INTO current_relay_status 
            (relay_number, status, last_updated) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (relay_number, status))

        # Voeg toe aan history
        c.execute('''
            INSERT INTO relay_status (relay_number, status, reason) 
            VALUES (?, ?, ?)
        ''', (relay_number, status, reason))

        conn.commit()
        conn.close()

        print(f"Relay {relay_number} {'AAN' if status else 'UIT'} - {reason}")
        return True

    except Exception as e:
        print(f"Fout bij instellen van relay {relay_number}: {e}")
        return False

def get_current_relay_status():
    """Haal huidige status van alle relays op uit database + sync met GPIO"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        SELECT relay_number, status, last_updated 
        FROM current_relay_status 
        ORDER BY relay_number
    ''')

    results = c.fetchall()
    conn.close()

    status_dict = {}
    for relay_num, status, last_updated in results:
        gpio_status = read_relay_status(relay_num)
        if gpio_status is not None and gpio_status != status:
            # Sync verschil corrigeren
            set_relay_status(relay_num, gpio_status, "sync_correction")
            status = gpio_status

        status_dict[relay_num] = {
            'status': status,
            'last_updated': last_updated,
            'gpio_status': gpio_status
        }

    return status_dict

def get_relay_history(relay_number, hours=24):
    """Haal historische data op voor een relay"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        SELECT timestamp, status, reason 
        FROM relay_status 
        WHERE relay_number = ? AND timestamp > datetime('now', ?)
        ORDER BY timestamp DESC
        LIMIT 100
    ''', (relay_number, f'-{hours} hours'))

    results = c.fetchall()
    conn.close()

    return [{'timestamp': ts, 'status': status, 'reason': reason}
            for ts, status, reason in results]

if __name__ == '__main__':
    # Test de relays
    print("Relays testen...")
    for relay_num in [1, 2]:
        print(f"Relay {relay_num} status voor test: {read_relay_status(relay_num)}")

        # Toggle test
        set_relay_status(relay_num, 1, "test")
        time.sleep(1)
        set_relay_status(relay_num, 0, "test")

        print(f"Relay {relay_num} status na test: {read_relay_status(relay_num)}")

    print("Huidige status uit database:", get_current_relay_status())
