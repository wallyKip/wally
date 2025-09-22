import RPi.GPIO as GPIO
import time

# Definieer de GPIO pinnen voor de relays
RELAY_1_PIN = 5  # Eerste relay op IO5
RELAY_2_PIN = 6  # Tweede relay op IO6

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_1_PIN, GPIO.OUT)
GPIO.setup(RELAY_2_PIN, GPIO.OUT)

# Zorg ervoor dat beide relays initial UIT staan
GPIO.output(RELAY_1_PIN, GPIO.LOW)
GPIO.output(RELAY_2_PIN, GPIO.LOW)

try:
    print("Test relay op GPIO 5 (IO5)...")
    # Relay 1 AAN
    GPIO.output(RELAY_1_PIN, GPIO.HIGH)
    print("Relay 1 AAN")
    time.sleep(2)
    
    # Relay 1 UIT
    GPIO.output(RELAY_1_PIN, GPIO.LOW)
    print("Relay 1 UIT")
    time.sleep(1)  # Korte pauze

    print("Test relay op GPIO 6 (IO6)...")
    # Relay 2 AAN
    GPIO.output(RELAY_2_PIN, GPIO.HIGH)
    print("Relay 2 AAN")
    time.sleep(2)
    
    # Relay 2 UIT
    GPIO.output(RELAY_2_PIN, GPIO.LOW)
    print("Relay 2 UIT")
    time.sleep(1)

    print("Test voltooid!")

finally:
    # Extra zekerheid: zet beide relays uit
    GPIO.output(RELAY_1_PIN, GPIO.LOW)
    GPIO.output(RELAY_2_PIN, GPIO.LOW)
    GPIO.cleanup()
    print("GPIO netjes opgeruimd.")
