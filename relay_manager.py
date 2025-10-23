#!/usr/bin/env python3
import sqlite3
from datetime import datetime
from gpio_manager import gpio_manager

DB_PATH = '/home/kip/wally/sensor_data.db'

def init_gpio():
    """Alleen voor backward compatibility - GPIO is al geïnitialiseerd"""
    pass

def set_relay_status(relay_number, status, reason="unknown"):
    """Set relay status en log naar database"""
    try:
        # Stuur naar hardware
        success = gpio_manager.set_relay(relay_number, status)
        
        if success:
            # Log naar database
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                INSERT INTO relay_status (relay_number, status, timestamp, reason)
                VALUES (?, ?, ?, ?)
            ''', (relay_number, status, datetime.now().isoformat(), reason))
            conn.commit()
            conn.close()
            return True
        return False
    except Exception as e:
        print(f"Error setting relay {relay_number}: {e}")
        return False

def read_relay_status(relay_number):
    """Read current relay status from hardware"""
    try:
        return gpio_manager.get_relay(relay_number)
    except Exception as e:
        print(f"Error reading relay {relay_number}: {e}")
        return None

def get_current_relay_status():
    """Get status of all relays from hardware"""
    return {
        1: {'status': read_relay_status(1), 'name': 'Warm Water'},
        2: {'status': read_relay_status(2), 'name': 'Radiatoren'}
    }