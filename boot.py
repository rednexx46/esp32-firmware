from time import sleep
from machine import reset
from espnow import ESPNow
from utils.config_reader import setup_config
from esp_network.espnow_comm import set_esp, set_sta
from esp_network.wifi_utils import connect_wifi

print("[BOOT] Starting boot...")

# === Load configuration ===
config = setup_config()
if not config:
    print("[BOOT] Failed to load config.ini. Rebooting...")
    sleep(2)
    reset()

# === Wi-Fi setup and RSSI ===
ssid = config["wifi_ssid"]
password = config["wifi_password"]
timeout = config["wifi_timeout"]
channel = config["wifi_channel"]

print("[BOOT] Loaded configuration:")
for k, v in config.items():
    print(f"  {k}: {v}")

sta, wifi_ok = connect_wifi(ssid, password, channel, timeout)

if wifi_ok:
    print(f"[BOOT] Connected to {ssid}.")
else:
    print("[BOOT] Failed to connect to AP.")

# === ESP-NOW Initialization ===
print("[ESP-NOW] Initializing...")
esp = ESPNow()
esp.active(True)
esp_key = config["esp_key"].encode()
if len(esp_key) != 16:
    print("[ESP-NOW] Invalid key length. Must be 16 bytes.")
    reset()
esp.add_peer(b'\xff' * 6)
print("[ESP-NOW] Broadcast peer added.")

# === Save global state ===
set_esp(esp)
set_sta(sta)

print("[BOOT] Boot complete.")
