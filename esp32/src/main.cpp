#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

/* =========================================================
   MATRIX CONFIGURATIE
   ========================================================= */
const int CS_PIN  = 21;
const int DIN_PIN = 23;
const int CLK_PIN = 18;

#define MATRICES 2  // Nog steeds 2 matrices aangesloten, maar gebruiken alleen de eerste

// buffer[matrix][rij]
uint8_t matrixBuffer[MATRICES][8];

/* =========================================================
   WIFI / API
   ========================================================= */
const char* ssid     = "MiloBoven";
const char* password = "mmmmmmmm";
const char* api_url  = "http://192.168.1.10/api/latest";

/* =========================================================
   GLOBAL STATE
   ========================================================= */
float tempWally = 0;
float tempRadiatoren = 0;

float tempTankBoven = 0, tempTankMidden = 0, tempTankOnder = 0;
float tempWWIngang = 0, tempWW = 0, tempWWUitgang = 0;

bool relay1Status = false;
bool relay2Status = false;

float previousTempWally = 0;
bool isTemperatureRising = false;

unsigned long lastTempCheckTime = 0;
const long tempCheckInterval = 600000;

const int buttonPin = 5;
bool lastButtonState = HIGH;

const long blinkInterval = 500;

// Buttons
const int toggleButtonPin = 19;   // direct toggle relay2
const int timerButtonPin  = 22;   // multi-click timer button

bool lastToggleButtonState = HIGH;
bool lastTimerButtonState  = HIGH;

unsigned long lastToggleButtonTime = 0;
unsigned long lastTimerButtonTime  = 0;

int timerClickCount = 0;
unsigned long timerClickStart = 0;

unsigned long pumpOffUntil = 0;
int timerHours = 0;

void setRelay2(bool on) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  String url = "http://192.168.1.10/relay/2/" + String(on ? "0" : "1");
  http.begin(url);

  int code = http.GET();
  if (code == 200) {
    relay2Status = on;
    Serial.println("Relay2 gezet naar: " + String(on));
  } else {
    Serial.println("Relay2 fout: " + String(code));
  }
  http.end();
}

void toggleRelay2() {
  setRelay2(!relay2Status);
}

void startPumpTimer(int hours) {
  timerHours = hours;
  pumpOffUntil = millis() + (unsigned long)hours * 60UL * 60UL * 1000UL;
  setRelay2(false);

  Serial.println("Timer gestart: " + String(hours) + " uur UIT");
}

void stopPumpTimer() {
  timerHours = 0;
  pumpOffUntil = 0;
  setRelay2(true);

  Serial.println("Timer gestopt, relay2 AAN");
}

void handleToggleButton() {
  static unsigned long lastPressTime = 0;
  const unsigned long debounceTime = 50;
  
  bool currentState = digitalRead(toggleButtonPin);
  
  // Detecteer RISING edge (LOW → HIGH) - button LOSGELATEN
  if (currentState == HIGH && lastToggleButtonState == LOW) {
    if (millis() - lastPressTime > debounceTime) {
      lastPressTime = millis();
      Serial.println("Button losgelaten - toggle actie!");
      
      if (timerHours > 0 || pumpOffUntil > millis()) {
        stopPumpTimer();
      } else {
        toggleRelay2();
      }
    }
  }
  
  lastToggleButtonState = currentState;
}

void handleTimerButton() {
  static unsigned long lastPressTime = 0;
  const unsigned long debounceTime = 50;
  
  bool currentState = digitalRead(timerButtonPin);
  
  // Detecteer RISING edge (LOW → HIGH) - button LOSGELATEN
  if (currentState == HIGH && lastTimerButtonState == LOW) {
    if (millis() - lastPressTime > debounceTime) {
      lastPressTime = millis();
      
      if (timerClickCount == 0) {
        timerClickStart = millis();
      }
      
      timerClickCount++;
      Serial.print("Timer click: ");
      Serial.println(timerClickCount);
    }
  }
  
  lastTimerButtonState = currentState;
  
  // na 1 sec geen klik → uitvoeren
  if (timerClickCount > 0 && millis() - timerClickStart > 1000) {
    Serial.print("Actie na 1 sec - aantal clicks: ");
    Serial.println(timerClickCount);
    
    if (timerClickCount == 1) {
      Serial.println("Start timer 1 uur");
      startPumpTimer(1);  // 1 uur
    } else if (timerClickCount == 2) {
      Serial.println("Start timer 2 uur");
      startPumpTimer(2);  // 2 uur
    } else if (timerClickCount == 3) {
      Serial.println("Start timer 3 uur");
      startPumpTimer(3);  // 3 uur
    } else if (timerClickCount >= 4) {
      Serial.println("Stop timer");
      stopPumpTimer();    // timer uitschakelen en pomp aan
    }
    timerClickCount = 0;
    Serial.print("timerHours na actie: ");
    Serial.println(timerHours);
  }
}

/* =========================================================
   MATRIX LOW LEVEL
   ========================================================= */
void sendCommandAll(uint8_t reg, uint8_t value) {
  digitalWrite(CS_PIN, LOW);
  for (int m = MATRICES - 1; m >= 0; m--) {
    SPI.transfer(reg);
    SPI.transfer(value);
  }
  digitalWrite(CS_PIN, HIGH);
}

void setupMatrix() {
  pinMode(CS_PIN, OUTPUT);
  digitalWrite(CS_PIN, HIGH);
  SPI.begin(CLK_PIN, -1, DIN_PIN, CS_PIN);

  sendCommandAll(0x0F, 0x00);
  sendCommandAll(0x0C, 0x01);
  sendCommandAll(0x09, 0x00);
  sendCommandAll(0x0B, 0x07);
  sendCommandAll(0x0A, 0x05);
}

void clearMatrix() {
  for (int m = 0; m < MATRICES; m++)
    for (int r = 0; r < 8; r++)
      matrixBuffer[m][r] = 0x00;
}

void refreshRow(uint8_t rij) {
  digitalWrite(CS_PIN, LOW);
  for (int m = MATRICES - 1; m >= 0; m--) {
    SPI.transfer(rij + 1);
    SPI.transfer(matrixBuffer[m][rij]);
  }
  digitalWrite(CS_PIN, HIGH);
}

void updateMatrix() {
  for (int r = 0; r < 8; r++) refreshRow(r);
}

void setPixel(int x, int y, bool aan) {
  // Extra check voor geldige waarden
  if (x < 0 || x > 15 || y < 0 || y > 7) {
    return;
  }

  int matrix = (x < 8) ? 0 : 1;
  int col = x % 8;
  
  // Veilige bit-operatie
  if (col >= 0 && col < 8) {
    uint8_t bit = 0x80 >> col;
    
    if (aan)
      matrixBuffer[matrix][y] |= bit;
    else
      matrixBuffer[matrix][y] &= ~bit;
  }
}

/* =========================================================
   MATRIX LOGICA - Aangepast voor 1 matrix
   ========================================================= */
void updateTankMatrix() {
  float somTank = tempTankBoven + tempTankMidden + tempTankOnder;
  int rijenAan = 0;

  if (somTank > 180) rijenAan = 8;
  else if (somTank > 167) rijenAan = 7;
  else if (somTank > 154) rijenAan = 6;
  else if (somTank > 141) rijenAan = 5;
  else if (somTank > 128) rijenAan = 4;
  else if (somTank > 111) rijenAan = 3;
  else if (somTank > 98)  rijenAan = 2;
  else if (somTank > 90)  rijenAan = 1;

  // Kolom 1 en 2 (nu 0-1 want we beginnen bij 0)
  for (int y = 7; y >= 8 - rijenAan; y--) {
    setPixel(0, y, true);  // Kolom 1
    setPixel(1, y, true);  // Kolom 2
  }
}

void updateWWMatrix() {
  int rijenAan = 0;

  if (tempWW <= 35) rijenAan = 0;
  else if (tempWW >= 50) rijenAan = 8;
  else rijenAan = map(tempWW, 35, 50, 1, 7);

  // Kolom 7 en 8 (nu 6-7)
  for (int y = 7; y >= 8 - rijenAan; y--) {
    setPixel(6, y, true);  // Kolom 7
    setPixel(7, y, true);  // Kolom 8
  }
}

void updateRelayMatrix() {
  // Relay 2: kolom 4-5, rij 1-2 (nu 3-4, 0-1)
  if (relay2Status) {
    for (int x = 3; x <= 4; x++) {
      for (int y = 0; y <= 1; y++) {
        setPixel(x, y, true);
      }
    }
  }

  // Relay 1: kolom 4-5, rij 7-8 (nu 3-4, 6-7)
  if (relay1Status) {
    for (int x = 3; x <= 4; x++) {
      for (int y = 6; y <= 7; y++) {
        setPixel(x, y, true);
      }
    }
  }
}

void updateSmileyMatrix() {
  float somTank = tempTankBoven + tempTankMidden + tempTankOnder;
  
  // EERST clear de timer LEDs (rij 6) om te voorkomen dat we oude LEDs laten branden
  for (int x = 9; x <= 8+6; x++) {
    setPixel(x, 6, false);
  }
  
  // Timer LEDs boven de ogen (alleen als timer actief is)
  if (timerHours > 0 && pumpOffUntil > millis()) {
    int aantalLeds = 0;
    
    // Bepaal aantal LEDs op basis van timer uren
    if (timerHours == 1) {
      aantalLeds = 2;  // 2 LEDs bij 1 uur
    } else if (timerHours == 2) {
      aantalLeds = 4;  // 4 LEDs bij 2 uur
    } else if (timerHours >= 3) {
      aantalLeds = 6;  // 6 LEDs bij 3 uur (max)
    }
    
    // LEDs boven de ogen plaatsen (rij 6) - in de juiste volgorde
    if (aantalLeds >= 2) {
      // Eerste paar LEDs (boven linker oog)
      setPixel(9, 6, true);
      setPixel(8+2, 6, true);
    }
    
    if (aantalLeds >= 4) {
      // Tweede paar LEDs (boven rechter oog)
      setPixel(8+5, 6, true);
      setPixel(8+6, 6, true);
    }
    
    if (aantalLeds >= 6) {
      // Derde paar LEDs (midden tussen ogen)
      setPixel(8+3, 6, true);
      setPixel(8+4, 6, true);
    }
  }
  
  // Clear de ogen eerst
  for (int x = 9; x <= 8+6; x++) {
    for (int y = 4; y <= 5; y++) {
      setPixel(x, y, false);
    }
  }
  
  // Ogen op basis van somTank
  if (somTank > 150) {
    // Grote ogen (2x2 pixels elk) - somTank > 150
    // Linker oog (kolom 1-2, rij 4-5)
    setPixel(9, 4, true);
    setPixel(8+2, 4, true);
    setPixel(9, 5, true);
    setPixel(8+2, 5, true);
    
    // Rechter oog (kolom 5-6, rij 4-5)
    setPixel(8+5, 4, true);
    setPixel(8+6, 4, true);
    setPixel(8+5, 5, true);
    setPixel(8+6, 5, true);
    
  } else {
    // Kleine ogen (1 pixel elk) - somTank ≤ 150
    setPixel(8+2, 5, true);  // Linker oog
    setPixel(8+5, 5, true);  // Rechter oog
  }
  
  // Clear de mond eerst
  for (int x = 9; x <= 8+6; x++) {
    for (int y = 0; y <= 2; y++) {
      setPixel(x, y, false);
    }
  }
  
  // Mond op basis van somTank
  if (somTank > 128) {
    // :) - Blije mond (oprijgende hoeken)
    for (int x = 2; x <= 5; x++) {
      setPixel(8+x, 1, true);  // Basis mondlijn
    }
    setPixel(9, 2, true);  // Linker mondhoek omhoog
    setPixel(8+6, 2, true);  // Rechter mondhoek omhoog
    
  } else if (somTank > 98) {
    // :| - Neutrale mond (rechte lijn)
    for (int x = 2; x <= 5; x++) {
      setPixel(8+x, 2, true);  // Rechte mondlijn
    }
    setPixel(9, 2, true);
    setPixel(8+6, 2, true);  
    
  } else {
    // :( - Bedroefde mond (neergaande hoeken)
    for (int x = 2; x <= 5; x++) {
      setPixel(8+x, 2, true);  // Basis mondlijn
    }
    setPixel(9, 1, true);  // Linker mondhoek omlaag
    setPixel(8+6, 1, true);  // Rechter mondhoek omlaag
  }
}

void updateTimerMatrix() {
  // Timer: kolom 4-5, rij 4-5 (nu 3-4, 3-4)
  // Dit was "nu nog niks" maar laat ik leeg voor toekomstig gebruik
  // Hier kun je later timer indicatoren toevoegen
}

void updateBlinkMatrix() {
  static bool blinkState = false;
  static unsigned long lastBlink = 0;

  if (millis() - lastBlink > blinkInterval) {
    blinkState = !blinkState;
    lastBlink = millis();
  }

  // 1️⃣ Temperatuur stijgt en >45 → LEDs aan (vast)
  if (isTemperatureRising && tempWally > 45) {
    for (int x = 3; x <= 4; x++) {        // Kolom 4-5
      for (int y = 3; y <= 4; y++) {      // Rij 4-5
        setPixel(x, y, true);
      }
    }
    return;
  }

  // 2️⃣ Temperatuur >73 → LEDs aan (vast)
  if (tempWally > 73) {
    for (int x = 3; x <= 4; x++) {        // Kolom 4-5
      for (int y = 3; y <= 4; y++) {      // Rij 4-5
        setPixel(x, y, true);
      }
    }
    return;
  }

  // 3️⃣ Niet stijgend + 65..73 → LEDs knipperen
  if (!isTemperatureRising && tempWally >= 65 && tempWally <= 73) {
    if (blinkState) {
      for (int x = 3; x <= 4; x++) {      // Kolom 4-5
        for (int y = 3; y <= 4; y++) {    // Rij 4-5
          setPixel(x, y, true);
        }
      }
    }
    return;
  }

  // 4️⃣ Anders: LEDs uit (tussen 46-64 of stijgend ≤45)
}

void updateAllMatrix() {
  clearMatrix();
  updateTankMatrix();
  updateWWMatrix();
  updateRelayMatrix();
  updateTimerMatrix();
  updateBlinkMatrix();
  updateSmileyMatrix(); 
  updateMatrix();
}

/* =========================================================
   TEMPERATURE / RELAY (Ongewijzigd)
   ========================================================= */
bool parseRelayStatus(String json, int relayNumber) {
  DynamicJsonDocument doc(1024);
  if (deserializeJson(doc, json)) return false;
  return doc[String(relayNumber)]["status"] == 1;
}

void getRelayStatus() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin("http://192.168.1.10/api/relay_status");
  if (http.GET() == 200) {
    String payload = http.getString();
    relay1Status = parseRelayStatus(payload, 1);
    relay2Status = !parseRelayStatus(payload, 2);
  }
  http.end();
}

float parseTemperature(String json, String sensor) {
  int p = json.indexOf(sensor);
  if (p < 0) return -999;
  int t = json.indexOf("temperature", p);
  if (t < 0) return -999;
  return json.substring(json.indexOf(":", t) + 1).toFloat();
}

void getTemperatureData() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(api_url);
  if (http.GET() == 200) {
    String payload = http.getString();
    tempWally = parseTemperature(payload, "Wally uitgang");
    tempTankBoven = parseTemperature(payload, "Grote tank boven");
    tempTankMidden = parseTemperature(payload, "Grote tank midden");
    tempTankOnder = parseTemperature(payload, "Grote tank onder");
    tempWW = parseTemperature(payload, "Warm water");
  }
  http.end();
}

void updateTemperatureTrend() {
  isTemperatureRising = tempWally > previousTempWally;
  previousTempWally = tempWally;
}

/* =========================================================
   SETUP / LOOP
   ========================================================= */
void setup() {
  Serial.begin(115200);

  pinMode(toggleButtonPin, INPUT_PULLUP);
  pinMode(timerButtonPin, INPUT_PULLUP);

  // Optioneel: debug output
  Serial.println("Setup complete");
  Serial.print("Toggle pin: "); Serial.println(digitalRead(toggleButtonPin));
  Serial.print("Timer pin: "); Serial.println(digitalRead(timerButtonPin));

  setupMatrix();
  clearMatrix();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi verbonden");
}

void loop() {
  static unsigned long lastData = 0;
  static unsigned long lastMatrix = 0;

  // Timer check - verbeterd met extra debug
  if (timerHours > 0) {
    if (millis() > pumpOffUntil) {
      Serial.println("Timer verlopen - tijd om pomp aan te zetten");
      stopPumpTimer();
    } else {
      // Debug: toon resterende tijd elke 10 seconden
      static unsigned long lastTimerDebug = 0;
      if (millis() - lastTimerDebug > 10000) {
        unsigned long remaining = (pumpOffUntil - millis()) / 1000;
        Serial.print("Timer nog actief - resterend: ");
        Serial.print(remaining / 60);
        Serial.println(" minuten");
        lastTimerDebug = millis();
      }
    }
  }

  handleToggleButton();
  handleTimerButton();

  if (millis() - lastData > 30000) {
    getTemperatureData();
    getRelayStatus();
    lastData = millis();
  }

  if (millis() - lastMatrix > 500) {
    updateAllMatrix();
    lastMatrix = millis();
  }

  if (millis() - lastTempCheckTime > tempCheckInterval) {
    updateTemperatureTrend();
    lastTempCheckTime = millis();
  }
}