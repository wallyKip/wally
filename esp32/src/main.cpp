#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <SSD1306Wire.h>
#include <ArduinoJson.h>

#include <DHT.h>

// DHT sensor configuratie
#define DHTPIN 5
#define DHTTYPE DHT11   // of DHT11 als je die hebt

DHT dht(DHTPIN, DHTTYPE);

float temperature = 0;
float humidity = 0;



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

float tempTankBoven = 0, tempTankMidden = 0, tempTankOnder = 0;
float tempWWIngang = 0, tempWW = 0, tempWWUitgang = 0;

float previousTempWally = 0;
unsigned long lastTempCheckTime = 0;
const long tempCheckInterval = 600000; // 10 minuten = 600000 ms
bool isTemperatureRising = false;

const int buttonPin = 4;
bool lastButtonState = HIGH;
bool pumpState = false;

unsigned long pumpOffUntil = 0;
int timerHours = 0;

bool lastTimerButtonState = HIGH;
unsigned long lastTimerButtonTime = 0;

void setup() {
  Serial.begin(115200);
  pinMode(12, OUTPUT);
  pinMode(13, OUTPUT);
  pinMode(14, OUTPUT);
  pinMode(15, INPUT_PULLUP);
  pinMode(buttonPin, INPUT_PULLUP);
  
  display.init();
  display.flipScreenVertically(); 
  display.setFont(ArialMT_Plain_16);
  display.drawString(0, 0, "Verbinden...");
  display.display();
  
  Serial.println("Start ESP32...");
  WiFi.begin(ssid, password);
  Serial.print("Verbinden met ");
  Serial.println(ssid);

  dht.begin();

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
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, json);
  
  if (!error) {
    return doc[String(relayNumber)]["status"] == 1;
  }
  
  return false;
}

void getRelayStatus() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin("http://192.168.1.10/api/relay_status");
    int httpCode = http.GET();
    
    if (httpCode == 200) {
      String payload = http.getString();
      relay1Status = parseRelayStatus(payload, 1);
      relay2Status = !parseRelayStatus(payload, 2); //moet omgekeerd ivm switch op relay
    }
    http.end();
  }
}

void updateLEDs() {
  digitalWrite(12, relay1Status);
  digitalWrite(14, relay2Status);
}

void togglePump() {
  Serial.println("Pomp was: " + String(relay2Status));
  bool newStatus = !relay2Status;
  
  // Stuur nieuwe status
  HTTPClient http;
  http.end();
  http.begin("http://192.168.1.10/relay/2/" + String(newStatus ? "0" : "1"));
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    relay2Status = newStatus;
    updateLEDs();
    Serial.println("Pomp nu: " + String(newStatus));
  } else {
    Serial.println("Fout bij set relay: " + String(httpCode));
  }
  http.end();
}

void handleButton() {
  static unsigned long lastButtonTime = 0;
  bool currentButtonState = digitalRead(buttonPin);
  
  if (currentButtonState == LOW && lastButtonState == HIGH && 
      millis() - lastButtonTime > 300) {
    
    lastButtonTime = millis();
    Serial.println("Button ingedrukt - toggle pomp");

    // ALS timer actief is, schakel timer UIT
    if (timerHours > 0 || pumpOffUntil > millis()) {
      Serial.println("Timer gestopt");
      timerHours = 0;
      pumpOffUntil = 0;
    }

    togglePump();
  }
  
  lastButtonState = currentButtonState;
}

void updateTemperatureTrend() {
  isTemperatureRising = (tempWally > previousTempWally);
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

void updateDisplay() {
  display.clear();
  
  // Kolom 1 (0-40 pixels) - Radiatoren & Wally
  display.setFont(ArialMT_Plain_24);
  display.drawString(0, 0, String(tempWally,0));
  display.drawString(0, 30, String(tempRadiatoren,0));
  

  display.setFont(ArialMT_Plain_10);
  // Timer indicator (x'en onder radiatoren)
  if (timerHours > 0) {
    String timerIndicators = "";
    for (int i = 0; i < timerHours; i++) {
      timerIndicators += "x";
    }
    display.drawString(0, 54, timerIndicators);
  }
  
  // Kolom 2 (45-85 pixels) - Grote tank
  display.setFont(ArialMT_Plain_16);
  display.drawString(45, 0, String(tempTankBoven,0));
  display.drawString(45, 18, String(tempTankMidden,0));
  display.drawString(45, 36, String(tempTankOnder,0));
  
  // Kolom 3 (90-128 pixels) - Warm water + DHT sensor
  display.setFont(ArialMT_Plain_24);
  display.drawString(90, 0, String(tempWW,0)); // Warm water
  
  // DHT sensor data
  if (temperature != -999) {
    display.drawString(90, 30, String(temperature,1) + "C");
  } else {
    display.drawString(90, 30, "--C");
  }
  
  display.display();
}


void getTemperatureData() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(api_url);
    int httpCode = http.GET();
    
    if (httpCode == 200) {
      String payload = http.getString();
      
      // Haal alle temperaturen op
      tempWally = parseTemperature(payload, "Wally uitgang");
      tempRadiatoren = parseTemperature(payload, "Naar radiatoren");
      tempTankBoven = parseTemperature(payload, "Grote tank boven");
      tempTankMidden = parseTemperature(payload, "Grote tank midden"); 
      tempTankOnder = parseTemperature(payload, "Grote tank onder");
      tempWWIngang = parseTemperature(payload, "Warm water ingang");
      tempWW = parseTemperature(payload, "Warm water");
      tempWWUitgang = parseTemperature(payload, "Warm water uitgang");
      
      updateDisplay(); // Toon nieuwe layout
    }
    http.end();
  }
}

void handleTimerButton() {
  bool currentState = digitalRead(15);
  
  // Alleen detecteren op neergaande flank (HIGH -> LOW)
  if (currentState == LOW && lastTimerButtonState == HIGH && 
      millis() - lastTimerButtonTime > 300) {
    
    Serial.println("TimerButton ingedrukt");
    lastTimerButtonTime = millis();
    
    // Button ingedrukt - cycle timer 0→1→2→3→4→5→0
    timerHours = (timerHours + 1) % 6;
    
    if (timerHours > 0) {
      Serial.println("TimerButton (timerHours > 0) if");
      pumpOffUntil = millis() + (timerHours * 3600000UL);
      if (relay2Status) { 
        togglePump(); // Zet pomp alleen uit als hij aan staat
      }
      Serial.println("Timer: " + String(timerHours) + " uur");
    } else {
      pumpOffUntil = 0; // Timer uitgezet
      Serial.println("Timer: uit");
    }
  }
  
  lastTimerButtonState = currentState;
}

void readDHT() {
  Serial.println("=== DHT11 Uitlezen ===");
  
  // Probeer meerdere keren
  for(int i = 0; i < 3; i++) {
    temperature = dht.readTemperature();
    humidity = dht.readHumidity();
    
    Serial.print("Poging "); Serial.print(i+1);
    Serial.print(": Temp="); Serial.print(temperature);
    Serial.print(", Hum="); Serial.println(humidity);
    
    if (!isnan(temperature) && !isnan(humidity)) {
      Serial.println("SUCCES! DHT11 werkt.");
      return;
    }
    delay(1000);
  }
  
  Serial.println("FOUT: DHT11 geeft geen data");
  temperature = -999;
  humidity = -999;
}

void loop() {
  handleButton();        // Aan/uit button
  handleTimerButton();   // Timer button
  blinkLED13();          // Temperatuur trend
  updateDisplay();       // Scherm continu updaten

  static unsigned long lastDataTime = 0;
  if (millis() - lastDataTime >= 30000) { // Elke 3 seconden
    getTemperatureData();
    getRelayStatus();
    updateLEDs();
    readDHT();
    lastDataTime = millis();
  }

    // Check timer - zet pomp aan als timer verstreken
  if (pumpOffUntil > 0 && millis() >= pumpOffUntil) {
    pumpOffUntil = 0;
    timerHours = 0;
    togglePump(); 
  }
}