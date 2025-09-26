#!/usr/bin/env python3
import sqlite3
import os

DB_PATH = '/home/kip/wally/sensor_data.db'

def create_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sensor_id TEXT NOT NULL,
            temperature REAL NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON sensor_readings(timestamp)
    ''')
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_sensor_id 
        ON sensor_readings(sensor_id)
    ''')
    
    conn.commit()
    conn.close()
    print("Database created successfully")

if __name__ == '__main__':
    create_database()