#!/usr/bin/env python3
import RPi.GPIO as GPIO
import threading

class GPIOManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GPIOManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if not self._initialized:
            GPIO.setmode(GPIO.BCM)
            # Relay pins (zelfde als in relay_manager.py)
            self.relay_pins = {1: 5, 2: 6}
            for pin in self.relay_pins.values():
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.HIGH)  # Relays zijn active LOW
            self._initialized = True
    
    def set_relay(self, relay_num, status):
        """Set relay status (0=UIT, 1=AAN)"""
        pin = self.relay_pins.get(relay_num)
        if pin is not None:
            # Active LOW: HIGH = uit, LOW = aan
            GPIO.output(pin, GPIO.LOW if status else GPIO.HIGH)
            return True
        return False
    
    def get_relay(self, relay_num):
        """Get relay status (0=UIT, 1=AAN)"""
        pin = self.relay_pins.get(relay_num)
        if pin is not None:
            # Active LOW: LOW = aan, HIGH = uit
            return 1 if GPIO.input(pin) == GPIO.LOW else 0
        return None

# Singleton instance
gpio_manager = GPIOManager()