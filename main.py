import time
import machine
import uos
from config_reader import load_config
from umqtt.simple import MQTTClient
from espnow_comm import get_esp, get_sta, get_wifi_status
from machine import Pin, ADC, I2C
from bme680 import BME680_I2C

# TODO: The sensor reading must be configured in the config.ini file
# TODO: Implement KPIs

# === Config ===
print("[BOOT] Loading configuration...")
config = load_config()
use_bme = config.get("SENSOR", {}).get("use_bme680", "false").lower() == "true"
use_ldr = config.get("SENSOR", {}).get("use_ldr", "false").lower() == "true"
mqtt_host = config.get("MQTT", {}).get("mqtt_broker", "broker.local")
mqtt_port = int(config.get("MQTT", {}).get("mqtt_port", 1883))
mqtt_user = config.get("MQTT", {}).get("mqtt_user")
mqtt_pass = config.get("MQTT", {}).get("mqtt_password")
print(f"[CONFIG] use_bme680={use_bme}, use_ldr={use_ldr}, mqtt_host={mqtt_host}, mqtt_port={mqtt_port}")
esp = get_esp()
sta = get_sta()
wifi_ok = get_wifi_status()
print(f"[WIFI] Wi-Fi status: {wifi_ok}")
ESP_NOW_KEY = config.get("ESP_NOW", {}).get("esp_key", "defaultfallback123")

BUFFER = []
BUFFER_FILE = "buffer.txt"
MAX_FAILURES = 3

# === Sensor Setup ===
print("[SENSOR] Setting up sensors...")
ldr = ADC(Pin(34)) if use_ldr else None
if ldr:
    ldr.atten(ADC.ATTN_11DB)
    print("[SENSOR] LDR sensor initialized.")
bme = BME680_I2C(i2c=I2C(scl=Pin(22), sda=Pin(21))) if use_bme else None
if bme:
    print("[SENSOR] BME680 sensor initialized.")

# === Helpers ===
def read_sensors():
    print("[SENSOR] Reading sensors...")
    if ldr:
        value = ldr.read()
        print(f"[SENSOR] LDR value: {value}")
        return f"LDR={value}".encode()
    if bme and bme.get_sensor_data():
        t = round(bme.data.temperature, 2)
        h = round(bme.data.humidity, 2)
        p = round(bme.data.pressure, 2)
        print(f"[SENSOR] BME680 values: T={t}C H={h}% P={p}hPa")
        return f"T={t}C H={h}% P={p}hPa".encode()
    print("[SENSOR] No sensor data available.")
    return b"no_data"

def load_buffer():
    buf = []
    try:
        with open(BUFFER_FILE, "r") as f:
            for line in f:
                buf.append(line.strip().encode())
        print(f"[NODE] Loaded {len(buf)} buffered items from file.")
    except:
        print("[NODE] No existing buffer file.")
    return buf

def save_buffer(buf):
    try:
        with open(BUFFER_FILE, "w") as f:
            for item in buf:
                f.write(item.decode() + "\n")
        print(f"[NODE] Saved {len(buf)} items to buffer file.")
    except Exception as e:
        print(f"[NODE] Failed to save buffer: {e}")

def recv_with_timeout(timeout_ms=3000):
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        host, msg = esp.recv()
        if msg:
            return host, msg
        time.sleep(0.05)
    return None, None

def can_be_gateway():
    print("[GATEWAY] Checking if device can be gateway...")
    try:
        client = MQTTClient("esp32", mqtt_host, port=mqtt_port, user=mqtt_user, password=mqtt_pass)
        client.connect()
        client.disconnect()
        print("[GATEWAY] MQTT connection successful. Can be gateway.")
        return True
    except Exception as e:
        print(f"[GATEWAY] MQTT connection failed: {e}")
        return False

def gateway_loop():
    print("[GATEWAY] I am GATEWAY. Listening ESP-NOW and publishing sensors...")
    client = MQTTClient("gateway", mqtt_host, port=mqtt_port, user=mqtt_user, password=mqtt_pass)
    client.connect()

    last_sensor_time = time.ticks_ms()

    while True:
        if not sta.isconnected():
            print("[GATEWAY] Wi-Fi lost. Resetting...")
            time.sleep(2)
            machine.reset()

        host, msg = esp.recv()
        if msg:
            if msg == b"DISCOVER_GATEWAY":
                mac = sta.config('mac')
                print(f"[GATEWAY] Responding to DISCOVER_GATEWAY from {host}")
                esp.send(host, b"I_AM_GATEWAY:" + mac)
            else:
                node_id = host.hex()
                topic = f"mesh/data/{node_id}"
                print(f"[GATEWAY] MQTT publish from node {node_id}: {msg}")
                client.publish(topic, msg)

        if time.ticks_diff(time.ticks_ms(), last_sensor_time) > 10000:
            payload = read_sensors()
            if payload:
                topic = "mesh/data/gateway"
                print(f"[GATEWAY] MQTT publish (own sensor): {payload}")
                client.publish(topic, payload)
            last_sensor_time = time.ticks_ms()

        time.sleep(0.1)

def node_loop():
    gateway_mac = None
    print("[NODE] I am NODE. Discovering gateway...")

    BUFFER[:] = load_buffer()
    consecutive_failures = 0

    def discover_gateway():
        nonlocal gateway_mac
        esp.send(b'\xff'*6, b"DISCOVER_GATEWAY")
        host, msg = recv_with_timeout()
        if msg and msg.startswith(b"I_AM_GATEWAY:"):
            gateway_mac = msg.split(b":")[1]
            esp.add_peer(gateway_mac, lmk=ESP_NOW_KEY)
            print(f"[NODE] Gateway found: {gateway_mac}")
            return True
        return False

    def send_payload(payload):
        MAX_SIZE = 240
        if len(payload) <= MAX_SIZE:
            esp.send(gateway_mac, payload)
        else:
            parts = [payload[i:i+MAX_SIZE] for i in range(0, len(payload), MAX_SIZE)]
            for idx, part in enumerate(parts):
                header = f"PART[{idx+1}/{len(parts)}]|".encode()
                esp.send(gateway_mac, header + part)
                time.sleep(0.05)

    last_read = time.ticks_ms()

    while True:
        if time.ticks_diff(time.ticks_ms(), last_read) >= 10000:
            payload = read_sensors()
            if payload:
                if len(BUFFER) < 20:
                    BUFFER.append(payload)
                    save_buffer(BUFFER)
                    print(f"[NODE] Buffered: {payload}")
                else:
                    print("[NODE] Buffer full. Discarding.")
            last_read = time.ticks_ms()

        if not gateway_mac:
            found = discover_gateway()
            if not found:
                print("[NODE] No gateway. Will retry...")
                time.sleep(5)
                continue

        i = 0
        while i < len(BUFFER):
            try:
                send_payload(BUFFER[i])
                print(f"[NODE] Sent buffered: {BUFFER[i]}")
                i += 1
                consecutive_failures = 0
            except Exception as e:
                print(f"[NODE] Send failed: {e}")
                consecutive_failures += 1
                if consecutive_failures >= MAX_FAILURES:
                    print("[NODE] Lost connection to gateway. Resetting discovery.")
                    gateway_mac = None
                break

        BUFFER[:] = BUFFER[i:]
        save_buffer(BUFFER)
        time.sleep(1)

# === MAIN ===
print("[MAIN] Starting main logic...")
if wifi_ok and can_be_gateway():
    print("[MAIN] Acting as gateway.")
    gateway_loop()
else:
    print("[MAIN] Acting as node.")
    ok = node_loop()
    if not ok:
        print("[MAIN] Waiting for retry...")
        time.sleep(10)
        print("[MAIN] Resetting device.")
        machine.reset()