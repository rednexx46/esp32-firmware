import time
import machine
import network
import espnow
from utils.config_reader import load_config
import espnow_comm
from network.wifi_utils import connect_wifi

print("[BOOT] Starting boot...")

# === Load configuration ===
config = load_config()
if not config:
    print("[BOOT] Failed to load config.ini. Rebooting...")
    time.sleep(2)
    machine.reset()

ssid = config.get("WIFI", {}).get("wifi_ssid")
password = config.get("WIFI", {}).get("wifi_password")
print(f"[BOOT] Wi-Fi SSID: {ssid}")

# === Enable Wi-Fi STA ===
sta = network.WLAN(network.STA_IF)
sta.active(True)

wifi_connected = connect_wifi(ssid, password)

# === Initialize ESP-NOW ===
print("[ESP-NOW] Initializing...")
esp = espnow.ESPNow()
esp.init()

esp_key = config.get("ESP_NOW", {}).get("esp_key", "").encode()
if len(esp_key) != 16:
    print("[ESP-NOW] Invalid key length. Must be 16 bytes.")
    machine.reset()

esp.add_peer(b'\xff' * 6, lmk=esp_key)
print("[ESP-NOW] Peer added and ready.")

# === Save global state ===
espnow_comm.set_esp(esp)
espnow_comm.set_sta(sta)
espnow_comm.set_wifi_status(wifi_connected)

print("[BOOT] Boot complete.")