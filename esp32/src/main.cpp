#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <ArduinoJson.h>

<<<<<<< HEAD
=======
SSD1306Wire display(0x3c, 21, 22);
>>>>>>> b5a65f03b29a8417608164bd9c80ce58fdbd9159
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

const int buttonPin = 5;              // CHANGED: Pomp button nu op D5
bool lastButtonState = HIGH;
bool pumpState = false;

unsigned long pumpOffUntil = 0;
int timerHours = 0;

bool lastTimerButtonState = HIGH;
unsigned long lastTimerButtonTime = 0;

// LED pins voor tank temperatuur
const int tankLEDs[] = {18, 15, 19, 21, 22};  // CHANGED: nieuwe volgorde
const int numTankLEDs = 5;

// LED pins voor warm water temperatuur
const int wwLEDs[] = {27, 26, 25, 33, 32};
const int numWWLEDs = 5;

// Timer LED pin
const int timerLED = 23;  // CHANGED: Timer LED nu op D23

void testAllLEDs() {
  Serial.println("Test alle LEDs...");
  
  // Zet alle tank LEDs aan
  for (int i = 0; i < numTankLEDs; i++) {
    digitalWrite(tankLEDs[i], HIGH);
  }
  
  // Zet alle warm water LEDs aan
  for (int i = 0; i < numWWLEDs; i++) {
    digitalWrite(wwLEDs[i], HIGH);
  }
  
  // Timer LED
  digitalWrite(timerLED, HIGH);
  
  // Ook de andere LEDs in je systeem
  digitalWrite(12, HIGH);
  digitalWrite(13, HIGH);
  digitalWrite(14, HIGH);
  
  // Houd alle LEDs 2 seconden aan
  delay(20000);
  
  // Zet alle LEDs uit
  for (int i = 0; i < numTankLEDs; i++) {
    digitalWrite(tankLEDs[i], LOW);
  }
  for (int i = 0; i < numWWLEDs; i++) {
    digitalWrite(wwLEDs[i], LOW);
  }
  
  digitalWrite(timerLED, LOW);
  digitalWrite(12, LOW);
  digitalWrite(13, LOW);
  digitalWrite(14, LOW);
  
  Serial.println("LED test voltooid");
}

void setup() {
  Serial.begin(115200);
  
  // Zet alle pin modes
  pinMode(12, OUTPUT);
  pinMode(13, OUTPUT);
  pinMode(14, OUTPUT);
  pinMode(2, INPUT_PULLUP);           // Timer button op D2
  pinMode(buttonPin, INPUT_PULLUP);   // Pomp button op D5
  
<<<<<<< HEAD
  // Zet pin modes voor tank temperatuur LEDs
  for (int i = 0; i < numTankLEDs; i++) {
    pinMode(tankLEDs[i], OUTPUT);
    digitalWrite(tankLEDs[i], LOW);
  }
  
  // Zet pin modes voor warm water LEDs
  for (int i = 0; i < numWWLEDs; i++) {
    pinMode(wwLEDs[i], OUTPUT);
    digitalWrite(wwLEDs[i], LOW);
  }
  
  // Zet pin mode voor timer LED (D23)
  pinMode(timerLED, OUTPUT);
  digitalWrite(timerLED, LOW);
  
  Serial.println("Start ESP32...");
  WiFi.begin(ssid, password);
  
  // Test alle LEDs
  testAllLEDs();
=======
  display.init();
  display.setFont(ArialMT_Plain_16);
  display.drawString(0, 0, "Verbinden...");
  display.display();
  
  Serial.println("Start ESP32...");
  WiFi.begin(ssid, password);
  Serial.print("Verbinden met ");
  Serial.println(ssid);
>>>>>>> b5a65f03b29a8417608164bd9c80ce58fdbd9159

  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 15000) {
    delay(500);
    Serial.print(".");
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

void updateTimerLED() {
  // Timer LED (D23) aan voor 1, 2 of 3 uur, uit voor 0 uur
  if (timerHours >= 1 && timerHours <= 3) {
    digitalWrite(timerLED, HIGH);
  } else {
    // FORCEER laag met kleine vertraging voor zekerheid
    digitalWrite(timerLED, LOW);
    delayMicroseconds(10); // Korte vertraging
    digitalWrite(timerLED, LOW); // Nogmaals voor zekerheid
  }
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
      updateTimerLED(); // Update timer LED
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
  } else if (isTemperatureRising && tempWally >= 65 && tempWally <= 75) {
    // Temperatuur stijgt tussen 65-75°C: LED altijd AAN
    digitalWrite(13, HIGH);
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

<<<<<<< HEAD
void updateTankLEDs() {
  float somTank = tempTankBoven + tempTankMidden + tempTankOnder;
  
  // Zet alle tank LEDs uit
  for (int i = 0; i < numTankLEDs; i++) {
    digitalWrite(tankLEDs[i], LOW);
  }
  
  // Zet LEDs aan gebaseerd op som temperatuur
  if (somTank > 180) {
    // Alle LEDs aan (18, 15, 19, 21, 22)
    for (int i = 0; i < numTankLEDs; i++) {
      digitalWrite(tankLEDs[i], HIGH);
    }
  } else if (somTank > 166) {
    // 4 LEDs aan (18, 15, 19, 21)
    for (int i = 0; i < 4; i++) {
      digitalWrite(tankLEDs[i], HIGH);
    }
  } else if (somTank > 134) {
    // 3 LEDs aan (18, 15, 19)
    for (int i = 0; i < 3; i++) {
      digitalWrite(tankLEDs[i], HIGH);
    }
  } else if (somTank > 112) {
    // 2 LEDs aan (18, 15)
    for (int i = 0; i < 2; i++) {
      digitalWrite(tankLEDs[i], HIGH);
    }
  } else if (somTank > 90) {
    // 1 LED aan (18)
    digitalWrite(tankLEDs[0], HIGH);
  }
=======
void updateDisplay() {
  display.clear();

  //
  // LINKERKOLOM – 2 GROTE REGELS
  //
  display.setFont(ArialMT_Plain_10);
  display.drawString(0, 0, "Wally");
  display.setFont(ArialMT_Plain_24);   // grote letters
  display.drawString(0, 8, "  " + String((int)tempWally));
  display.setFont(ArialMT_Plain_10);
  display.drawString(0, 34, "Warm Water");
  display.setFont(ArialMT_Plain_24);
  display.drawString(0, 41, "  " +  String((int)tempWW));

  //
  // RECHTERKOLOM – 3 KLEINE REGELS
  //
  display.setFont(ArialMT_Plain_16);

  display.drawString(90, 0,  String((int)tempTankBoven));
  display.drawString(90, 22, String((int)tempTankMidden));
  display.drawString(90, 44, String((int)tempTankOnder));

  display.display();
>>>>>>> b5a65f03b29a8417608164bd9c80ce58fdbd9159
}

void updateWWLEDs() {
  // Zet alle WW LEDs uit
  for (int i = 0; i < numWWLEDs; i++) {
    digitalWrite(wwLEDs[i], LOW);
  }
  
  // Zet LEDs aan gebaseerd op tempWW
  if (tempWW > 60) {
    // Alle LEDs aan (27, 26, 25, 33, 32)
    for (int i = 0; i < numWWLEDs; i++) {
      digitalWrite(wwLEDs[i], HIGH);
    }
  } else if (tempWW > 53) {
    // 4 LEDs aan (27, 26, 25, 33)
    for (int i = 0; i < 4; i++) {
      digitalWrite(wwLEDs[i], HIGH);
    }
  } else if (tempWW > 47) {
    // 3 LEDs aan (27, 26, 25)
    for (int i = 0; i < 3; i++) {
      digitalWrite(wwLEDs[i], HIGH);
    }
  } else if (tempWW > 41) {
    // 2 LEDs aan (27, 26)
    for (int i = 0; i < 2; i++) {
      digitalWrite(wwLEDs[i], HIGH);
    }
  } else if (tempWW > 35) {
    // 1 LED aan (27)
    digitalWrite(wwLEDs[0], HIGH);
  }
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
      
<<<<<<< HEAD
      // Update de LED indicaties
      updateTankLEDs();
      updateWWLEDs();
=======
      updateDisplay();
>>>>>>> b5a65f03b29a8417608164bd9c80ce58fdbd9159
    }
    http.end();
  }
}

void handleTimerButton() {
  bool currentState = digitalRead(2);  // Timer button op D2
  
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
    
    // Update timer LED
    updateTimerLED();
  }
  
  lastTimerButtonState = currentState;
}

void loop() {
  handleButton();        // Aan/uit button op D5
  handleTimerButton();   // Timer button op D2
  blinkLED13();          // Temperatuur trend

  static unsigned long lastDataTime = 0;
  if (millis() - lastDataTime >= 30000) { // Elke 30 seconden
    getTemperatureData();
    getRelayStatus();
    updateLEDs();
    lastDataTime = millis();
  }

  // Check timer - zet pomp aan als timer verstreken
  if (pumpOffUntil > 0 && millis() >= pumpOffUntil) {
    pumpOffUntil = 0;
    timerHours = 0;
    updateTimerLED(); // Zet timer LED uit
    togglePump(); 
  }
}