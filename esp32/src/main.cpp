#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <SSD1306Wire.h>

SSD1306Wire display(0x3c, 21, 22);
const char* ssid = "MiloBoven";
const char* password = "mmmmmmmm";
const char* api_url = "http://192.168.1.10/api/latest";

// Global variables
float tempWally = 0;
float tempRadiatoren = 0;
unsigned long previousBlinkMillis = 0;
const long blinkInterval = 500;
bool ledState = false;
bool relay1Status = false;
bool relay2Status = false;

float previousTempWally = 0;
unsigned long lastTempCheckTime = 0;
const long tempCheckInterval = 600000; // 10 minuten = 600000 ms
bool isTemperatureRising = false;

const int buttonPin = 4;
bool lastButtonState = HIGH;
bool pumpState = false;

void setup() {
  Serial.begin(115200);
  pinMode(12, OUTPUT);
  pinMode(13, OUTPUT);
  pinMode(14, OUTPUT);
  pinMode(buttonPin, INPUT_PULLUP);
  
  display.init();
  display.setFont(ArialMT_Plain_16);
  display.drawString(0, 0, "Verbinden...");
  display.display();
  
  Serial.println("Start ESP32...");
  WiFi.begin(ssid, password);
  Serial.print("Verbinden met ");
  Serial.println(ssid);

  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 15000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nVerbonden! IP: " + WiFi.localIP().toString());
    
    // TOEVOEGEN: Update display na verbinding
    display.clear();
    display.drawString(0, 0, "Verbonden!");
    display.drawString(0, 20, WiFi.localIP().toString());
    display.display();
    
  } else {
    Serial.println("\nNiet verbonden");
    display.clear();
    display.drawString(0, 0, "WiFi fout!");
    display.display();
  }
}

bool parseRelayStatus(String json, int relayNumber) {
  String searchPattern = "\"" + String(relayNumber) + "\":{\"status\":1";
  return (json.indexOf(searchPattern) != -1);
}

void getRelayStatus() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin("http://192.168.1.10/api/relay_status");
    int httpCode = http.GET();
    
    if (httpCode == 200) {
      String payload = http.getString();
      relay1Status = parseRelayStatus(payload, 0);
      relay2Status = parseRelayStatus(payload, 1);
    }
    http.end();
  }
}

void updateLEDs() {
  digitalWrite(12, relay1Status);
  digitalWrite(14, relay2Status);
}

void togglePump() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    // Eerst huidige status ophalen
    http.begin("http://192.168.1.10/api/relay_status");
    int httpCode = http.GET();
    
    if (httpCode == 200) {
      String payload = http.getString();
      bool currentStatus = parseRelayStatus(payload, 1);
      
      // Toggle de status
      bool newStatus = !currentStatus;
      
      // Stuur nieuwe status
      http.end();
      http.begin("http://192.168.1.10/relay/2/" + String(newStatus ? "1" : "0"));
      httpCode = http.GET();
      
      if (httpCode == 200) {
        Serial.println("Pomp getoggled: " + String(newStatus ? "AAN" : "UIT"));
      } else {
        Serial.println("Fout bij set relay: " + String(httpCode));
      }
    } else {
      Serial.println("Fout bij ophalen status: " + String(httpCode));
    }
    http.end();
  }
}

void handleButton() {
  bool currentButtonState = digitalRead(buttonPin);
  
  if (currentButtonState == LOW) {
    // Button ingedrukt - toggle pomp (Relay 1)
      Serial.println("button ingedrukt");
    togglePump();
    delay(50);  // Debounce
  }
  
  lastButtonState = currentButtonState;
}

void updateTemperatureTrend() {
  if (previousTempWally != 0) { // Alleen vergelijken als we vorige meting hebben
    isTemperatureRising = (tempWally > previousTempWally);
    
    Serial.print("Temperatuur trend: ");
    Serial.print(previousTempWally);
    Serial.print(" -> ");
    Serial.print(tempWally);
    Serial.println(isTemperatureRising ? " (STIJGEND)" : " (DALEND)");
  }
  
  previousTempWally = tempWally;
}

void blinkLED13() {
  unsigned long currentMillis = millis();
  
  // Elke 10 minuten temperatuur trend bijwerken
  if (currentMillis - lastTempCheckTime >= tempCheckInterval) {
    updateTemperatureTrend();
    lastTempCheckTime = currentMillis;
  }
  
  // Logica voor LED 13
  if (tempWally > 75) {
    // Boven 75°C: LED altijd AAN
    digitalWrite(13, HIGH);
    // Serial.println("LED13: AAN (temp > 75)");
  } else if (isTemperatureRising && tempWally >= 65 && tempWally <= 75) {
    // Temperatuur stijgt tussen 65-75°C: LED altijd AAN
    digitalWrite(13, HIGH);
    // Serial.println("LED13: AAN (stijgend)");
  } else if (!isTemperatureRising && tempWally >= 65 && tempWally <= 75) {
    // Temperatuur daalt tussen 65-75°C: LED knipperen
    if (currentMillis - previousBlinkMillis >= blinkInterval) {
      previousBlinkMillis = currentMillis;
      ledState = !ledState;
      digitalWrite(13, ledState);
      Serial.println(ledState ? "LED13: Knipper AAN" : "LED13: Knipper UIT");
    }
  } else {
    // Anders: LED UIT
    digitalWrite(13, LOW);
    ledState = false;
  }
}

float parseTemperature(String json, String sensorName) {
  int sensorPos = json.indexOf("\"" + sensorName + "\"");
  if (sensorPos == -1) return -999;
  
  int tempPos = json.indexOf("\"temperature\":", sensorPos);
  if (tempPos == -1) return -999;
  
  int valueStart = json.indexOf(":", tempPos) + 1;
  int valueEnd = json.indexOf(",", valueStart);
  if (valueEnd == -1) valueEnd = json.indexOf("}", valueStart);
  
  String tempStr = json.substring(valueStart, valueEnd);
  tempStr.trim();
  
  return tempStr.toFloat();
}

void getTemperatureData() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(api_url);
    int httpCode = http.GET();
    
    if (httpCode == 200) {
      String payload = http.getString();
      tempWally = parseTemperature(payload, "Wally uitgang");
      tempRadiatoren = parseTemperature(payload, "Naar radiatoren");
      
      display.clear();
      display.drawString(0, 0, "Wally: " + String(tempWally,0) + "C" + (isTemperatureRising ? "↑" : "↓"));
      display.drawString(0, 20, "Radiatoren: " + String(tempRadiatoren,0) + "C");
      display.display();
    }
    http.end();
  }
}

void loop() {
  handleButton();        // Check button input
  blinkLED13();

  static unsigned long lastDataTime = 0;
  if (millis() - lastDataTime >= 3000) { // Elke 3 seconden
    getTemperatureData();
    getRelayStatus();
    updateLEDs();

    Serial.println("relay 0: " + String(relay1Status));
    Serial.println("relay 1: " + String(relay1Status));
    lastDataTime = millis();
  }
}