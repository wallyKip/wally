import gpiod
import sqlite3
from datetime import datetime

DB_PATH = '/home/kip/wally/sensor_data.db'
CHIP_NAME = "gpiochip0"

# Interne cache
_gpio_chip = None
_relay_lines = {}

RELAY_GPIO_MAP = {
    1: 5,
    2: 6
}

def _get_gpio_chip():
    global _gpio_chip
    if _gpio_chip is None:
        _gpio_chip = gpiod.Chip(CHIP_NAME)
    return _gpio_chip

def _get_line_for_relay(relay_num):
    if relay_num not in RELAY_GPIO_MAP:
        raise ValueError(f"Relay {relay_num} niet gedefinieerd in RELAY_GPIO_MAP")
    
    if relay_num not in _relay_lines:
        chip = _get_gpio_chip()
        line = chip.get_line(RELAY_GPIO_MAP[relay_num])
        line.request(consumer="relay_manager", type=gpiod.LINE_REQ_DIR_OUT)
        _relay_lines[relay_num] = line
    
    return _relay_lines[relay_num]

def set_relay_status(relay_num, status, source="unknown"):
    """Zet de status van een relay aan of uit"""
    line = _get_line_for_relay(relay_num)
    line.set_value(1 if status else 0)
    log_relay_status(relay_num, status, source)
    return True

def read_relay_status(relay_num):
    """Leest huidige status van een relay"""
    line = _get_line_for_relay(relay_num)
    return line.get_value()

def log_relay_status(relay_num, status, source="unknown"):
    """Log de status in de database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS relay_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            relay_number INTEGER NOT NULL,
            status INTEGER NOT NULL,
            source TEXT
        )
    ''')
    
    c.execute(
        "INSERT INTO relay_status (relay_number, status, source) VALUES (?, ?, ?)",
        (relay_num, status, source)
    )
    
    conn.commit()
    conn.close()
