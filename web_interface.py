#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import sqlite3
import json
from datetime import datetime, timedelta
from relay_manager import init_gpio, get_current_relay_status, set_relay_status

init_gpio() 

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

RELAY_NAMES = {
    1: "Radiatoren",
    2: "Warm Water"
}

def get_latest_readings():
    """Haal de laatste meting voor elke sensor op"""
    conn = sqlite3.connect(DB_PATH)
     
    c = conn.cursor()
    
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

def get_relay_history(relay_number, hours=24):
    """Haal historische data op voor een specifieke relay"""
    conn = sqlite3.connect(DB_PATH)
     
    c = conn.cursor()

    since_time = datetime.now() - timedelta(hours=hours)

    c.execute('''
        SELECT timestamp, status, reason 
        FROM relay_status 
        WHERE relay_number = ? AND timestamp > ?
        ORDER BY timestamp DESC
    ''', (relay_number, since_time))

    results = c.fetchall()
    conn.close()

    return [
        {'timestamp': ts, 'status': status, 'reason': reason}
        for ts, status, reason in results
    ]


class SensorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_main_page()
        elif self.path.startswith('/relay/'):
            self.handle_relay_control()
        elif self.path == '/api/relay_status':
            self.serve_api_relay_status()
        elif self.path == '/api/latest':
            self.serve_api_latest()
        elif self.path.startswith('/api/history/'):
            self.serve_api_history()
        elif self.path.startswith('/api/relay_history/'):
            self.serve_api_relay_history()
        else:
            self.send_error(404)
    
    def serve_main_page(self):
        sensor_data = get_latest_readings()
        relay_status = get_current_relay_status()
        
        html = f"""<html>
<head>
    <title>Wally</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; margin: 15px 0; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .relay-on {{ background-color: #d4edda; }}
        .relay-off {{ background-color: #f8d7da; }}
        .relay-btn {{ padding: 5px 10px; margin: 2px; cursor: pointer; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>Wally </h1>    
    <table>
        <tr><th>Sensor</th><th>Temperatuur</th><th>Laatste meting</th></tr>"""
        
        for sensor_name, data in sensor_data.items():
            html += f"""
        <tr>
            <td>{sensor_name}</td>
            <td><strong>{data['temperature']:.1f} °C</strong></td>
            <td class="timestamp">{data['timestamp']}</td>
        </tr>"""
        
        html += """
    </table>
    
    <h2>Pompen</h2>
    <table>
        <tr><th>Relay</th><th>Status</th><th>Laatste update</th><th>Actie</th></tr>"""
        
        last_updated_1 = relay_status[1]['last_updated']
        timestamp_1 = datetime.strptime(last_updated_1, '%Y-%m-%d %H:%M:%S')
        time_diff_1 = (datetime.now() - timestamp_1).total_seconds() / 3600  # uren
        warning_1 = " ⚠️" if time_diff_1 > 2.083 else "bla"  # 2u5min = 2.083 uur

        # Relay 1 - Radiatoren
        html += f"""
        <tr class="{'relay-on' if relay_status[1]['status'] else 'relay-off'}">
            <td><strong>Warm Water</strong></td>
            <td>{'AAN' if relay_status[1]['status'] else 'UIT'}</td>
            <td class="timestamp">{relay_status[1]['last_updated']}{warning_1}kjgkjgh</td>
            <td>
                <button class="relay-btn" onclick="setRelay(1, 1)">AAN</button>
                <button class="relay-btn" onclick="setRelay(1, 0)">UIT</button>
            </td>
        </tr>"""
        
        # Relay 2 - Warm Water
        html += f"""
        <tr class="{'relay-off' if relay_status[2]['status'] else 'relay-on'}">
            <td><strong>Radiatoren</strong></td>
            <td>{'UIT' if relay_status[2]['status'] else 'AAN'}</td>
            <td class="timestamp">{relay_status[2]['last_updated']}</td>
            <td>
                <button class="relay-btn" onclick="setRelay(2, 0)">AAN</button>
                <button class="relay-btn" onclick="setRelay(2, 1)">UIT</button>
            </td>
        </tr>"""
        
        html += """
    </table>
    
    <script>
    function setRelay(relayNum, status) {
        fetch('/relay/' + relayNum + '/' + status)
            .then(response => {
                if(response.ok) {
                    location.reload();
                }
            });
    }
    </script>
    
    <p><a href="/api/latest">JSON API</a> | <a href="/api/relay_status">Relay Status API</a></p>
    <p><em>Data wordt elke minuut verzameld. Pagina vernieuwt niet automatisch.</em></p>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def handle_relay_control(self):
        """Verwerk relay bediening via URL /relay/<nummer>/<status>"""
        try:
            parts = self.path.split('/')
            relay_number = int(parts[2])
            new_status = int(parts[3])
            
            if relay_number in [1, 2] and new_status in [0, 1]:
                success = set_relay_status(relay_number, new_status, "web_control")
                
                if success:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b"OK")
                else:
                    self.send_error(500)
            else:
                self.send_error(400)
                
        except Exception as e:
            print(f"Relay control error: {e}")
            self.send_error(400)
    
    def serve_api_relay_status(self):
        relay_status = get_current_relay_status()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(relay_status, indent=2).encode())
    
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

    def serve_api_relay_history(self):
        try:
            relay_number = int(self.path.split('/')[-1])
            history = get_relay_history(relay_number, hours=24)

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