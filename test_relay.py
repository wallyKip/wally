from relay_manager import init_gpio, read_relay_status, set_relay_status

print("=== RELAY DEBUG ===")

# INITIALISEER EERST!
print("Initialiseer GPIO...")
init_gpio()

print(f"Relay 1 status: {read_relay_status(1)}")

# Test toggle
print("Zet relay AAN...")
set_relay_status(1, 1, "debug_test")
print(f"Relay 1 status na aan: {read_relay_status(1)}")

print("Zet relay UIT...")
set_relay_status(1, 0, "debug_test")
print(f"Relay 1 status na uit: {read_relay_status(1)}")