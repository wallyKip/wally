#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import time

# DEFINIEER HIER JE EIGEN SENSOR NAMEN
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

RELAY_GPIO_PIN = 5  # GPIO pin voor de relay
RELAY_STATE_FILE = "/tmp/relay_state.txt"  # Bestand om status op te slaan

# Initialiseer GPIO
def setup_gpio():
    # Export GPIO pin als deze niet geëxporteerd is
    if not os.path.exists(f'/sys/class/gpio/gpio{RELAY_GPIO_PIN}'):
        try:
            with open('/sys/class/gpio/export', 'w') as f:
                f.write(str(RELAY_GPIO_PIN))
            time.sleep(0.1)  # Wacht even
        except Exception as e:
            print(f"GPIO export error: {e}")
    
    # Zet pin mode naar output
    try:
        with open(f'/sys/class/gpio/gpio{RELAY_GPIO_PIN}/direction', 'w') as f:
            f.write('out')
    except Exception as e:
        print(f"GPIO direction error: {e}")

# Lees relay status uit bestand
def read_relay_state():
    try:
        with open(RELAY_STATE_FILE, 'r') as f:
            return f.read().strip() == '1'
    except FileNotFoundError:
        # Maak bestand aan met standaard status UIT
        write_relay_state(False)
        return False

# Schrijf relay status naar bestand
def write_relay_state(state):
    try:
        with open(RELAY_STATE_FILE, 'w') as f:
            f.write('1' if state else '0')
    except Exception as e:
        print(f"Write state error: {e}")

# Update fysieke GPIO pin
def update_gpio_state(state):
    try:
        with open(f'/sys/class/gpio/gpio{RELAY_GPIO_PIN}/value', 'w') as f:
            f.write('1' if state else '0')
    except Exception as e:
        print(f"GPIO write error: {e}")

# Initialisatie
setup_gpio()
current_relay_state = read_relay_state()
update_gpio_state(current_relay_state)

class SensorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global current_relay_state
        
        # Relay bediening verwerken
        if 'relay=toggle' in self.path:
            # Toggle de status
            current_relay_state = not current_relay_state
            write_relay_state(current_relay_state)
            update_gpio_state(current_relay_state)
            time.sleep(0.5)  # Kleine vertraging voor feedback
        
        sensor_data = {}
        
        # Lees temperaturen van alle gespecificeerde sensoren
        for sensor_id, sensor_name in SENSOR_MAPPING.items():
            sensor_path = os.path.join("/sys/bus/w1/devices", sensor_id, "w1_slave")
            try:
                with open(sensor_path, 'r') as f:
                    content = f.read()
                    if 'YES' in content:
                        temp_line = content.split('t=')[-1]
                        temp_c = float(temp_line) / 1000.0
                        sensor_data[sensor_name] = f"{temp_c:.1f} °C"
                    else:
                        sensor_data[sensor_name] = "CRC Error"
            except FileNotFoundError:
                sensor_data[sensor_name] = "Niet gevonden"
            except Exception as e:
                sensor_data[sensor_name] = f"Error: {e}"

        # Bouw de HTML response
        status_color = "#44ff44" if current_relay_state else "#ff4444"
        status_text = "AAN" if current_relay_state else "UIT"
        
        html = f"""<html>
<head>
    <title>Temperatuur Monitoring</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .relay-box {{ 
            margin: 20px 0; 
            padding: 15px; 
            border: 2px solid #ccc; 
            border-radius: 8px; 
            background-color: #f9f9f9;
            max-width: 300px;
        }}
        .status-indicator {{
            width: 20px; 
            height: 20px; 
            border-radius: 50%; 
            margin-right: 10px;
            border: 2px solid #000;
            display: inline-block;
            background-color: {status_color};
        }}
        button {{
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            margin-bottom: 10px;
        }}
        button:hover {{ background-color: #45a049; }}
    </style>
</head>
<body>
    <h1>🏠 Temperatuur Monitoring</h1>
    
    <table>
        <tr><th>Sensor</th><th>Temperatuur</th></tr>"""
        
        for sensor_name, temp in sensor_data.items():
            html += f"<tr><td>{sensor_name}</td><td>{temp}</td></tr>"
        
        html += f"""</table>
        
    <div class="relay-box">
        <h2>⏻ Pomp Bediening</h2>
        <form method='GET'>
            <input type='hidden' name='relay' value='toggle'>
            <button type='submit'>Pomp AAN/UIT</button>
        </form>
        <div style='margin-top: 10px; display: flex; align-items: center;'>
            <div class="status-indicator"></div>
            <span style='font-weight: bold;'>Status: {status_text}</span>
        </div>
    </div>
    
    <p><small>🔄 Auto-refresh elke 30 seconden</small></p>
    <script>setTimeout(function(){{location.reload();}}, 30000);</script>
</body>
</html>"""

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

# Start server op poort 8000
if __name__ == '__main__':
    print("Initialiseren... Zorg dat GPIO en status bestand klaar zijn.")
    print("Server draait op http://0.0.0.0:8000")
    httpd = HTTPServer(('', 8000), SensorHandler)
    httpd.serve_forever()
