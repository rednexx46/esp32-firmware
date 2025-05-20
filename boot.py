import time
import machine
import network
import espnow
from config_reader import load_config
import espnow_comm

print("[BOOT] Starting boot.py...")

# === Load configuration ===
print("[BOOT] Loading configuration...")
config = load_config()
if not config:
    print("[ERROR] Failed to load config.ini.")
    time.sleep(2)
    machine.reset()
else:
    print("[BOOT] Configuration loaded successfully.")

ssid = config.get("WIFI", {}).get("wifi_ssid")
password = config.get("WIFI", {}).get("wifi_password")
print(f"[BOOT] Wi-Fi SSID: {ssid}")

# === Enable Wi-Fi STA ===
print("[BOOT] Enabling Wi-Fi STA interface...")
sta = network.WLAN(network.STA_IF)
sta.active(True)
print("[BOOT] Wi-Fi STA interface enabled.")

def connect_wifi(ssid, password, timeout=10):
    if not sta.isconnected():
        print("[WIFI] Connecting to Wi-Fi...")
        sta.connect(ssid, password)
        for i in range(timeout):
            if sta.isconnected():
                print(f"[WIFI] Connected successfully: {sta.ifconfig()}")
                return True
            print(f"[WIFI] Waiting for connection... ({i+1}/{timeout})")
            time.sleep(1)
    if sta.isconnected():
        print(f"[WIFI] Already connected: {sta.ifconfig()}")
    else:
        print("[WIFI] Failed to connect to Wi-Fi.")
    return sta.isconnected()

wifi_connected = connect_wifi(ssid, password)

# === Initialize ESP-NOW ===
print("[ESP-NOW] Initializing ESP-NOW...")
esp = espnow.ESPNow()
esp.init()
esp_key = config.get("ESP_NOW", {}).get("esp_key")
if len(esp_key) != 16:
    print("Error: esp_key must contain 16 chars.")
    machine.reset()
print("[ESP-NOW] Adding peer with AES key...")
esp.add_peer(b'\xff'*6, lmk=esp_key.encode())
print("[ESP-NOW] ESP-NOW initialized and peer added.")

# Store globally
print("[BOOT] Storing ESP-NOW and Wi-Fi status globally...")
espnow_comm.set_esp(esp)
espnow_comm.set_sta(sta)
espnow_comm.set_wifi_status(wifi_connected)
print("[BOOT] Boot process completed.")
