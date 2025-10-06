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
  pinMode(12, OUTPUT);  // LED voor Relay 1 - Radiatoren
  pinMode(13, OUTPUT);  // KNIPPERT - Temperatuur trend
  pinMode(14, OUTPUT);  // LED voor Relay 2 - Warm Water
  pinMode(buttonPin, INPUT_PULLUP); // voor button
  
  display.init();
  display.setFont(ArialMT_Plain_16);
  display.drawString(0, 0, "Verbinden...");
  display.display();
  
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);
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

      relay1Status = parseRelayStatus(payload, 1);
      relay2Status = parseRelayStatus(payload, 2);
    }
    http.end();
  }
}

void updateLEDs() {
  digitalWrite(12, !relay1Status);
  digitalWrite(14, !relay2Status);
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
  
  // Sla huidige temperatuur op voor volgende vergelijking
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
    // } else {
    //   display.clear();
    //   display.drawString(0, 0, "HTTP Fout: " + String(httpCode));
    //   display.display();
    }
    http.end();
  }
}

void loop() {
  blinkLED13();  // Gebruikt globale tempWally

  // bool currentButtonState = digitalRead(buttonPin);
  
  // Serial.print("current: " + String(lastButtonState ? "AAN" : "UIT")); 
  // Serial.print("last: " + String(lastButtonState ? "AAN" : "UIT"));

  // if (lastButtonState == HIGH && currentButtonState == LOW) {
  //   // Button ingedrukt - toggle pomp
  //   pumpState = !pumpState;
  //   digitalWrite(12, pumpState);  // Stuur relay aan
    
  //   Serial.println("Pomp: " + String(pumpState ? "AAN" : "UIT"));
  //   delay(50);  // Debounce
  // }
  // lastButtonState = currentButtonState;

  static unsigned long lastDataTime = 0;
  if (millis() - lastDataTime >= 30000) {
    getTemperatureData();  // Update globale variables
    getRelayStatus();
    updateLEDs();
    lastDataTime = millis();
  }
}