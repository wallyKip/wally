#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import sqlite3
import json
from datetime import datetime, timedelta

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

def get_latest_readings():
    """Haal de laatste meting voor elke sensor op"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Haal laatste meting per sensor op
    c.execute('''
        SELECT sr.sensor_id, sr.temperature, sr.timestamp
        FROM sensor_readings sr
        INNER JOIN (
            SELECT sensor_id, MAX(timestamp) as max_timestamp
            FROM sensor_readings
            GROUP BY sensor_id
        ) latest ON sr.sensor_id = latest.sensor_id AND sr.timestamp = latest.max_timestamp
    ''')
    
    results = c.fetchall()
    conn.close()
    
    # Formatteer data
    sensor_data = {}
    for sensor_id, temperature, timestamp in results:
        sensor_name = SENSOR_MAPPING.get(sensor_id, sensor_id)
        sensor_data[sensor_name] = {
            'temperature': temperature,
            'timestamp': timestamp
        }
    
    return sensor_data

def get_sensor_history(sensor_id, hours=24):
    """Haal historische data op voor een sensor"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    since_time = datetime.now() - timedelta(hours=hours)
    
    c.execute('''
        SELECT timestamp, temperature 
        FROM sensor_readings 
        WHERE sensor_id = ? AND timestamp > ?
        ORDER BY timestamp
    ''', (sensor_id, since_time))
    
    results = c.fetchall()
    conn.close()
    
    return [{'timestamp': ts, 'temperature': temp} for ts, temp in results]

class SensorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_main_page()
        elif self.path == '/api/latest':
            self.serve_api_latest()
        elif self.path.startswith('/api/history/'):
            self.serve_api_history()
        else:
            self.send_error(404)
    
    def serve_main_page(self):
        sensor_data = get_latest_readings()
        
        html = f"""<html>
<head>
    <title>Wally</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; margin: 15px 0; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>Wally</h1>
    <p>Laatste update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <table>
        <tr>
            <th>Sensor</th>
            <th>Temperatuur</th>
            <th>Laatste meting</th>
        </tr>"""
        
        for sensor_name, data in sensor_data.items():
            html += f"""
        <tr>
            <td>{sensor_name}</td>
            <td><strong>{data['temperature']:.1f} °C</strong></td>
            <td class="timestamp">{data['timestamp']}</td>
        </tr>"""
        
        html += """
    </table>
    
    <p><a href="/api/latest">JSON API</a> | 
       <a href="/api/history/28-0b24a04fc39f">Voorbeeld historie</a></p>
    <p><em>Data wordt elke minuut verzameld. Pagina vernieuwt niet automatisch.</em></p>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_api_latest(self):
        sensor_data = get_latest_readings()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(sensor_data, indent=2).encode())
    
    def serve_api_history(self):
        try:
            sensor_id = self.path.split('/')[-1]
            history = get_sensor_history(sensor_id, hours=24)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(history, indent=2).encode())
        except:
            self.send_error(400)

if __name__ == '__main__':
    print("Web Interface gestart op http://0.0.0.0:8000")
    httpd = HTTPServer(('', 8000), SensorHandler)
    httpd.serve_forever()