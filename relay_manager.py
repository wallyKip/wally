#!/usr/bin/env python3
import sqlite3
import gpiod
from datetime import datetime

DB_PATH = '/home/kip/wally/sensor_data.db'
CHIP_NAME = 'gpiochip0'
RELAY_PINS = {
    1: 5,
    2: 6
}

# Init GPIO chip en lijnen (éénmalig)
chip = gpiod.Chip(CHIP_NAME)
relay_lines = {}

def read_relay_status_oneshot(relay_number):
    """Lees GPIO status van de opgegeven relay zonder lijnen vast te houden"""
    pin = RELAY_PINS.get(relay_number)
    if pin is None:
        return None
    try:
        chip = gpiod.Chip(CHIP_NAME)
        line = chip.get_line(pin)
        line.request(consumer="relay_manager", type=gpiod.LINE_REQ_DIR_IN)
        value = line.get_value()
        line.release()
        chip.close()
        return value
    except Exception as e:
        print(f"Fout bij lezen van relay {relay_number} (oneshot): {e}")
        return None

def init_gpio():
    """Initialiseer GPIO-lijnen indien nog niet gedaan"""
    global relay_lines
    if relay_lines:
        return  # Al geïnitialiseerd

    for relay_num, pin in RELAY_PINS.items():
        line = chip.get_line(pin)
        try:
            line.request(consumer="relay_manager", type=gpiod.LINE_REQ_DIR_OUT)
            relay_lines[relay_num] = line
        except OSError as e:
            print(f"GPIO {pin} voor Relay {relay_num} al bezet: {e}")

#init_gpio()  # automatisch bij import

def set_relay_status(relay_number, status, reason="manual"):
    """Zet relay aan of uit en log naar database"""
    line = relay_lines.get(relay_number)
    if not line:
        print(f"Relay {relay_number} niet geïnitialiseerd")
        return False

    try:
        line.set_value(1 if status else 0)

        conn = sqlite3.connect(DB_PATH)
         
        c = conn.cursor()

        # Update current status
        c.execute('''
            INSERT OR REPLACE INTO current_relay_status 
            (relay_number, status, last_updated) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (relay_number, status))

        # Log history
        c.execute('''
            INSERT INTO relay_status (relay_number, status, reason) 
            VALUES (?, ?, ?)
        ''', (relay_number, status, reason))

        conn.commit()
        conn.close()

        print(f"Relay {relay_number} {'AAN' if status else 'UIT'} - {reason}")
        return True
    except Exception as e:
        print(f"Fout bij relay {relay_number}: {e}")
        return False

def read_relay_status(relay_number):
    """Lees GPIO status van de opgegeven relay"""
    line = relay_lines.get(relay_number)
    if not line:
        return None
    try:
        return line.get_value()
    except Exception as e:
        print(f"Fout bij lezen van relay {relay_number}: {e}")
        return None

def get_current_relay_status():
    """Haal huidige status van relays uit database + sync met GPIO"""
    conn = sqlite3.connect(DB_PATH)
     
    c = conn.cursor()
    c.execute('''
        SELECT relay_number, status, last_updated 
        FROM current_relay_status 
        WHERE relay_number IN (1, 2)
    ''')
    db_results = c.fetchall()
    conn.close()

    status_dict = {}

    for relay_num, db_status, last_updated in db_results:
        gpio_status = read_relay_status(relay_num)
        if gpio_status is not None and gpio_status != db_status:
            # Sync mismatch, corrigeer DB
            set_relay_status(relay_num, gpio_status, reason="sync_correction")
            db_status = gpio_status

        status_dict[relay_num] = {
            'status': db_status,
            'gpio_status': gpio_status,
            'last_updated': last_updated
        }

    return status_dict

def get_relay_history(relay_number, hours=24):
    """Haal relay geschiedenis op"""
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
    return [{'timestamp': ts, 'status': s, 'reason': r} for ts, s, r in results]

# Test alleen bij direct uitvoeren
if __name__ == '__main__':
    print("Relay Test")
    for num in [1, 2]:
        print(f"Relay {num}: {read_relay_status(num)}")
        set_relay_status(num, 1, "test")
        time.sleep(1)
        set_relay_status(num, 0, "test")
