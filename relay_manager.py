#!/usr/bin/env python3
import sqlite3
import os
import time
from datetime import datetime

DB_PATH = '/home/kip/wally/sensor_data.db'
RELAY_GPIO_PINS = {1: 5, 2: 6}  # relay_number: gpio_pin

def setup_gpio():
    """Initialiseer GPIO pinnen voor relays"""
    for relay_num, gpio_pin in RELAY_GPIO_PINS.items():
        gpio_path = f'/sys/class/gpio/gpio{gpio_pin}'
        
        if not os.path.exists(gpio_path):
            try:
                with open('/sys/class/gpio/export', 'w') as f:
                    f.write(str(gpio_pin))
                time.sleep(0.1)
            except Exception as e:
                print(f"GPIO export error for pin {gpio_pin}: {e}")
        
        try:
            with open(f'{gpio_path}/direction', 'w') as f:
                f.write('out')
        except Exception as e:
            print(f"GPIO direction error for pin {gpio_pin}: {e}")

def read_relay_status(relay_number):
    """Lees huidige status van een relay"""
    gpio_pin = RELAY_GPIO_PINS.get(relay_number)
    if not gpio_pin:
        return None
    
    try:
        with open(f'/sys/class/gpio/gpio{gpio_pin}/value', 'r') as f:
            return int(f.read().strip())
    except:
        return None

def set_relay_status(relay_number, status, reason="manual"):
    """Zet relay status en sla op in database"""
    gpio_pin = RELAY_GPIO_PINS.get(relay_number)
    if not gpio_pin:
        return False
    
    try:
        # Stuur naar GPIO
        with open(f'/sys/class/gpio/gpio{gpio_pin}/value', 'w') as f:
            f.write('1' if status else '0')
        
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
        print(f"Error setting relay {relay_number}: {e}")
        return False

def get_current_relay_status():
    """Haal huidige status van alle relays op uit database"""
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
        # Verifieer met GPIO
        gpio_status = read_relay_status(relay_num)
        if gpio_status is not None and gpio_status != status:
            # Database en GPIO zijn niet synced, corrigeer database
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
    setup_gpio()
    
    # Test de relays
    print("Testing relays...")
    for relay_num in [1, 2]:
        print(f"Relay {relay_num} current status: {read_relay_status(relay_num)}")
        
        # Toggle test
        set_relay_status(relay_num, 1, "test")
        time.sleep(1)
        set_relay_status(relay_num, 0, "test")
        
        print(f"Relay {relay_num} status after test: {read_relay_status(relay_num)}")
    
    print("Current status from database:", get_current_relay_status())