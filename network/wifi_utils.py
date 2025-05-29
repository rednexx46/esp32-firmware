import network
import time

def connect_wifi(ssid, password, timeout=10):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if sta.isconnected():
        return sta, True

    sta.connect(ssid, password)
    for i in range(timeout):
        if sta.isconnected():
            return sta, True
        time.sleep(1)
    return sta, False