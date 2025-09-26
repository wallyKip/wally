#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import sqlite3
import json
from datetime import datetime, timedelta
from relay_manager import get_current_relay_status, set_relay_status, get_relay_history

DB_PATH = '/home/pi/wally/sensor_data.db'
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
    1: "Pomp CV",
    2: "Extra Relay"
}

def get_latest_readings():
    # ... (zelfde als voorheen)

class SensorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_main_page()
        elif self.path.startswith('/relay/'):
            self.handle_relay_control()
        elif self.path == '/api/relay_status':
            self.serve_api_relay_status()
        else:
            # ... (andere routes hetzelfde houden)
    
    def serve_main_page(self):
        sensor_data = get_latest_readings()
        relay_status = get_current_relay_status()
        
        html = f"""<html>
<head>
    <title>Temperatuur & Relay Monitoring</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; margin: 15px 0; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .relay-on {{ background-color: #d4edda; }}
        .relay-off {{ background-color: #f8d7da; }}
        .relay-btn {{ padding: 5px 10px; margin: 2px; cursor: pointer; }}
    </style>
</head>
<body>
    <h1>🏠 Temperatuur & Relay Monitoring</h1>
    <p>Laatste update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>🌡️ Temperatuur Sensoren</h2>
    <table>
        <tr><th>Sensor</th><th>Temperatuur</th><th>Laatste meting</th></tr>"""
        
        for sensor_name, data in sensor_data.items():
            html += f"""
        <tr>
            <td>{sensor_name}</td>
            <td><strong>{data['temperature']:.1f} °C</strong></td>
            <td>{data['timestamp']}</td>
        </tr>"""
        
        html += """
    </table>
    
    <h2>⏻ Relay Bediening</h2>
    <table>
        <tr><th>Relay</th><th>Status</th><th>Laatste update</th><th>Actie</th></tr>"""
        
        for relay_num, status_info in relay_status.items():
            status = status_info['status']
            status_class = "relay-on" if status else "relay-off"
            status_text = "AAN" if status else "UIT"
            relay_name = RELAY_NAMES.get(relay_num, f"Relay {relay_num}")
            
            html += f"""
        <tr class="{status_class}">
            <td><strong>{relay_name}</strong></td>
            <td>{status_text}</td>
            <td>{status_info['last_updated']}</td>
            <td>
                <button class="relay-btn" onclick="setRelay({relay_num}, 1)">AAN</button>
                <button class="relay-btn" onclick="setRelay({relay_num}, 0)">UIT</button>
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

# ... (rest van de code hetzelfde)

if __name__ == '__main__':
    print("Web Interface gestart op http://0.0.0.0:8000")
    httpd = HTTPServer(('', 8000), SensorHandler)
    httpd.serve_forever()