from utils.config_reader import setup_config
from core.sensor import setup_sensors
from esp_network.espnow_comm import get_esp, get_sta, get_role, set_role
from core.gateway import gateway_loop, start_gateway_beacon
from core.node import node_loop, start_node_beacon
from esp_network.role_selector import elect_role
from ble.ble_server import BLEServer
from machine import reset
from time import sleep
from gc import collect
from esp_network.wifi_utils import connect_wifi

def stop_ble_server(ble_server):
    if ble_server:
        try:
            ble_server.stop()
        except Exception as e:
            print(f"[MAIN] BLE server stop error: {e}")
        finally:
            return None
    return ble_server

def main():
    print("[MAIN] Booting system...")

    try:
        # Load configuration and initialize sensors
        config = setup_config()
        ldr, bme = setup_sensors(config)

        # Initialize networking
        esp = get_esp()
        sta = get_sta()
        ble_server = None
        node_interval = config["node_beacon_interval"]
        gateway_interval = config["gateway_beacon_interval"]

        while True:

            # Try to connect to Wi-Fi
            if not sta.isconnected():
                connect_wifi(config["wifi_ssid"], config["wifi_password"], config["wifi_channel"], config["wifi_timeout"])

            if get_role() != "gateway":
                set_role(elect_role(sta, esp))
            
            role = get_role()

            # Stop BLE server before switching roles
            ble_server = stop_ble_server(ble_server)

            if role == "gateway":
                print("[MAIN] Acting as GATEWAY")
                start_gateway_beacon(esp, sta.status("rssi"), gateway_interval)
                gateway_loop(config, esp, sta, ldr, bme)
                collect()
                sleep(gateway_interval + 1)

            if role == "node":
                print("[MAIN] Acting as NODE")
                if not ble_server:
                    try:
                        print("[MAIN] Starting BLE server...")
                        ble_server = BLEServer(sta)
                    except Exception as e:
                        print(f"[MAIN] BLE init error: {e}")
                start_node_beacon(esp, node_interval)
                node_loop(config, esp, sta, ldr, bme)
                collect()
                set_role(None)
                sleep(node_interval + 1)

    except Exception as e:
        print(f"[MAIN] Unhandled fatal error: {e}. Resetting in 10s...")
        sleep(10)
        reset()

if __name__ == "__main__":
    main()
