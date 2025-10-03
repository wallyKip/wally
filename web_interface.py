#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import sqlite3
import json
from datetime import datetime, timedelta
from relay_manager import init_gpio, get_current_relay_status, set_relay_status

init_gpio() 

DB_PATH = '/home/kip/wally/sensor_data.db'
SENSOR_MAPPING = {
    "28-0b24a04fc39f": "Naar radiatoren",
    "28-0b24a0539bdb": "Grote tank boven",
    "28-0b24a0545ad2": "Grote tank midden",
    "28-0b24a0507904": "Grote tank onder",
    "28-0b24a0569043": "Wally uitgang",
    "28-0b24a050eaec": "Warm water",
    "28-0b24a03a4d26": "Warm water ingang",
    "28-0b24a0551b3c": "Warm water uitgang"
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
        h1 {{ background-color:#d2f8d2;border:1px;border-radius: 5px;box-shadow: 2px 2px;margin:4px;padding:8px;font-size: 6em; }}
        table {{ width:100%;background-color:#d2f8d2;order:1px;border-radius: 5px;box-shadow: 2px 2px;margin:4px; }}
        th, td {{ background-color:#d2f8d2; border: 1px solid #ddd; padding: 8px; text-align: left; font-weight: bold; font-size: 6em; }}
        th {{ background-color: #f2f2f2; }}
        .relay-on {{ background-color: #d4edda; }}
        .relay-off {{ background-color: #f8d7da; }}
        .relay-btn {{ padding: 5px 10px; margin: 2px; cursor: pointer; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>""" 
    
        # Sensor E - Wally uitgang
        sensor_e_data = sensor_data.get("Wally uitgang", {})
        temp_e = sensor_e_data.get('temperature', 'N/A')
        timestamp_e = sensor_e_data.get('timestamp', '')
        if timestamp_e:
            time_diff_e = (datetime.now() - datetime.strptime(timestamp_e, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600
            warning_e = " <span style='color: red; font-weight: bold;'>&#9888;</span>" if time_diff_e > 2.083 else ""
        else:
            warning_e = " <span style='color: red; font-weight: bold;'>&#9888;</span>"
        
        html += f"""
        <h1>Wally<br>{temp_e if temp_e != 'N/A' else 'N/A'} &deg;C {warning_e}</h1>
        """
        
        # Sensor A - Naar radiatoren
        sensor_a_data = sensor_data.get("Naar radiatoren", {})
        temp_a = sensor_a_data.get('temperature', 'N/A')
        timestamp_a = sensor_a_data.get('timestamp', '')
        if timestamp_a:
            time_diff_a = (datetime.now() - datetime.strptime(timestamp_a, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600
            warning_a = " <span style='color: red; font-weight: bold;'>&#9888;</span>" if time_diff_a > 2.083 else ""
        else:
            warning_a = " <span style='color: red; font-weight: bold;'>&#9888;</span>"
        
        html += f"""
        <br>
        <h1>Naar radiatoren<br>{temp_a if temp_a != 'N/A' else 'N/A'} &deg;C {warning_e}</h1>
        <br> 
        """
        
        # Sensor B - Grote tank boven
        sensor_b_data = sensor_data.get("Grote tank boven", {})
        temp_b = sensor_b_data.get('temperature', 'N/A')
        timestamp_b = sensor_b_data.get('timestamp', '')
        if timestamp_b:
            time_diff_b = (datetime.now() - datetime.strptime(timestamp_b, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600
            warning_b = " <span style='color: red; font-weight: bold;'>&#9888;</span>" if time_diff_b > 2.083 else ""
        else:
            warning_b = " <span style='color: red; font-weight: bold;'>&#9888;</span>"
        
        html += f"""
        <table style="width:100%;">
        <tr>
            <td rowspan="3">Grote tank</td>
            <td><strong>{temp_b if temp_b != 'N/A' else 'N/A'} &deg;C</strong>{warning_b}</td>
        </tr>"""
        
        # Sensor C - Grote tank midden
        sensor_c_data = sensor_data.get("Grote tank midden", {})
        temp_c = sensor_c_data.get('temperature', 'N/A')
        timestamp_c = sensor_c_data.get('timestamp', '')
        if timestamp_c:
            time_diff_c = (datetime.now() - datetime.strptime(timestamp_c, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600
            warning_c = " <span style='color: red; font-weight: bold;'>&#9888;</span>" if time_diff_c > 2.083 else ""
        else:
            warning_c = " <span style='color: red; font-weight: bold;'>&#9888;</span>"
        
        html += f"""
        <tr>
            <td><strong>{temp_c if temp_c != 'N/A' else 'N/A'} &deg;C</strong>{warning_c}</td>
        </tr>"""
        
        # Sensor D - Grote tank onder
        sensor_d_data = sensor_data.get("Grote tank onder", {})
        temp_d = sensor_d_data.get('temperature', 'N/A')
        timestamp_d = sensor_d_data.get('timestamp', '')
        if timestamp_d:
            time_diff_d = (datetime.now() - datetime.strptime(timestamp_d, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600
            warning_d = " <span style='color: red; font-weight: bold;'>&#9888;</span>" if time_diff_d > 2.083 else ""
        else:
            warning_d = " <span style='color: red; font-weight: bold;'>&#9888;</span>"
        
        html += f"""
        <tr>
            <td><strong>{temp_d if temp_d != 'N/A' else 'N/A'} &deg;C</strong>{warning_d}</td>
        </tr></table>
        <br>
        <table>"""
        
        
        # Sensor G - Warm water ingang
        sensor_g_data = sensor_data.get("Warm water ingang", {})
        temp_g = sensor_g_data.get('temperature', 'N/A')
        timestamp_g = sensor_g_data.get('timestamp', '')
        if timestamp_g:
            time_diff_g = (datetime.now() - datetime.strptime(timestamp_g, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600
            warning_g = " <span style='color: red; font-weight: bold;'>&#9888;</span>" if time_diff_g > 2.083 else ""
        else:
            warning_g = " <span style='color: red; font-weight: bold;'>&#9888;</span>"
        
        html += f"""
        <tr>
            <td rowspan="3">Warm water</td>
            <td><span style="font-weight:normal;font-size:0.5em;">in </span><strong>{temp_g if temp_g != 'N/A' else 'N/A'} &deg;C</strong>{warning_g}</td>
        </tr>"""

        # Sensor F - Warm water
        sensor_f_data = sensor_data.get("Warm water", {})
        temp_f = sensor_f_data.get('temperature', 'N/A')
        timestamp_f = sensor_f_data.get('timestamp', '')
        if timestamp_f:
            time_diff_f = (datetime.now() - datetime.strptime(timestamp_f, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600
            warning_f = " <span style='color: red; font-weight: bold;'>&#9888;</span>" if time_diff_f > 2.083 else ""
        else:
            warning_f = " <span style='color: red; font-weight: bold;'>&#9888;</span>"
        
        html += f"""
        <tr>
            <td><strong>{temp_f if temp_f != 'N/A' else 'N/A'} &deg;C</strong>{warning_f}</td>
        </tr>"""
        
        # Sensor H - Warm water uitgang
        sensor_h_data = sensor_data.get("Warm water uitgang", {})
        temp_h = sensor_h_data.get('temperature', 'N/A')
        timestamp_h = sensor_h_data.get('timestamp', '')
        if timestamp_h:
            time_diff_h = (datetime.now() - datetime.strptime(timestamp_h, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600
            warning_h = " <span style='color: red; font-weight: bold;'>&#9888;</span>" if time_diff_h > 2.083 else ""
        else:
            warning_h = " <span style='color: red; font-weight: bold;'>&#9888;</span>"
        
        html += f"""
        <tr>
            <td><span style="font-weight:normal;font-size:0.5em;">uit </span><strong>{temp_h if temp_h != 'N/A' else 'N/A'} &deg;C</strong>{warning_h}</td>
        </tr>"""
        
        html += """
    </table>
    
    <h2>Pompen</h2>
    <table>
        <tr><th>Relay</th><th>Status</th><th>Laatste update</th><th>Actie</th></tr>"""
        # Relay 1 - Radiatoren
        html += f"""
        <tr class="{'relay-on' if relay_status[1]['status'] else 'relay-off'}">
            <td><button class="relay-btn" onclick="setRelay(1, {1 if not relay_status[1]['status'] else 0})"><strong>Warm Water</strong></button></td>
            <td>{'AAN' if relay_status[1]['status'] else 'UIT'}</td>
        </tr>"""
        
        # Relay 2 - Warm Water
        html += f"""
        <tr class="{'relay-on' if relay_status[2]['status'] else 'relay-off'}">
            <td><button class="relay-btn" onclick="setRelay(2, {1 if not relay_status[2]['status'] else 0})"><strong>Radiatoren</strong></button></td>
            <td>{'AAN' if relay_status[2]['status'] else 'UIT'}</td>
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
    <table>
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
    httpd = HTTPServer(('', 80), SensorHandler)
    httpd.serve_forever()