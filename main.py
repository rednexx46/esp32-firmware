from utils.config_reader import setup_config
from core.sensor import setup_sensors
from network.espnow_comm import get_esp, get_sta, get_wifi_status
from mqtt_utils import can_be_gateway
from gateway import gateway_loop
from node import node_loop
import machine
import time

print("[BOOT] Starting system...")

config = setup_config()
ldr, bme = setup_sensors(config)

esp = get_esp()
sta = get_sta()
wifi_ok = get_wifi_status()

if wifi_ok and can_be_gateway(config):
    print("[MAIN] Acting as gateway.")
    gateway_loop(config, esp, sta, ldr, bme)
else:
    print("[MAIN] Acting as node.")
    ok = node_loop(config, esp, sta, ldr, bme)
    if not ok:
        print("[MAIN] Waiting before reset...")
        time.sleep(10)
        machine.reset()