from network import WLAN, STA_IF
from time import sleep

def connect_wifi(ssid, password, wifi_channel, timeout=10):
    sta = WLAN(STA_IF)
    sta.active(True)
    sta.config(channel=wifi_channel)

    print(f"[WIFI] Trying to connect to SSID: '{ssid}'")

    if not ssid or not password:
        print("[WIFI] SSID or password is empty.")
        return sta, False

    sta.connect(ssid, password)

    for i in range(timeout):
        if sta.isconnected():
            print(f"[WIFI] Connected! IP: {sta.ifconfig()[0]}")
            return sta, True
        print(f"[WIFI] Waiting... {i+1}/{timeout}")
        sleep(5)

    print(f"[WIFI] Failed to connect after {timeout} seconds.")
    return sta, False
