#!/usr/bin/env python3
import sqlite3
import time
import gpiod
from datetime import datetime

DB_PATH = '/home/kip/wally/sensor_data.db'
CHIP_NAME = 'gpiochip0'

RELAY1_GPIO = 5
RELAY2_GPIO = 6

# GPIO state
_chip = None
_relay_lines = {}

def _ensure_gpio_initialized():
    global _chip, _relay_lines

    if _chip is None:
        _chip = gpiod.Chip(CHIP_NAME)
    
    if not _relay_lines:
        for num in [RELAY1_GPIO, RELAY2_GPIO]:
            line = _chip.get_line(num)
            line.request(consumer="relay_manager", type=gpiod.LINE_REQ_DIR_OUT)
            _relay_lines[num] = line

def set_relay_status(relay_number, status, reason="manual"):
    """Zet relay aan of uit en log naar database"""
    _ensure_gpio_initialized()

    gpio_number = RELAY1_GPIO if relay_number == 1 else RELAY2_GPIO if relay_number == 2 else None
    if gpio_number is None or gpio_number not in _relay_lines:
        print(f"Relay {relay_number} niet beschikbaar")
        return False

    try:
        line = _relay_lines[gpio_number]
        line.set_value(1 if status else 0)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('''
            INSERT OR REPLACE INTO current_relay_status 
            (relay_number, status, last_updated) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (relay_number, status))

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
    """Lees huidige GPIO status"""
    _ensure_gpio_initialized()

    gpio_number = RELAY1_GPIO if relay_number == 1 else RELAY2_GPIO if relay_number == 2 else None
    line = _relay_lines.get(gpio_number)
    return line.get_value() if line else None

def get_current_relay_status():
    """Lees status van beide relays uit DB + sync met GPIO"""
    _ensure_gpio_initialized()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        SELECT relay_number, status, last_updated 
        FROM current_relay_status 
        WHERE relay_number IN (1, 2)
        ORDER BY relay_number
    ''')

    results = c.fetchall()
    conn.close()

    status_dict = {}

    for relay_num, status, last_updated in results:
        gpio_status = read_relay_status(relay_num)
        if gpio_status is not None and gpio_status != status:
            # Sync mismatch → corrigeer database
            set_relay_status(relay_num, gpio_status, "sync_correction")
            status = gpio_status

        status_dict[relay_num] = {
            'status': status,
            'last_updated': last_updated,
            'gpio_status': gpio_status
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

    return [{'timestamp': ts, 'status': status, 'reason': reason} for ts, status, reason in results]

if __name__ == '__main__':
    # Test
    print("Relays testen...")
    for relay_num in [1, 2]:
        print(f"Relay {relay_num} status voor test: {read_relay_status(relay_num)}")
        set_relay_status(relay_num, 1, "test")
        time.sleep(1)
        set_relay_status(relay_num, 0, "test")
        print(f"Relay {relay_num} status na test: {read_relay_status(relay_num)}")

    print("Huidige status uit database:", get_current_relay_status())
