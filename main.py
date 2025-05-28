import time
import machine
import ujson
from config_reader import load_config
from umqtt.simple import MQTTClient
from espnow_comm import get_esp, get_sta, get_wifi_status
from machine import Pin, ADC, I2C
from bme680 import BME680_I2C

# === Config ===
print("[BOOT] Loading configuration...")
config = load_config()
kpi_interval = int(config.get("KPI", {}).get("kpi_interval", 60000))
sensor_read_interval = int(config.get("SENSOR", {}).get("sensor_read_interval", 30000))
use_bme = config.get("SENSOR", {}).get("use_bme680", "false").lower() == "true"
bme_sda_pin = int(config.get("SENSOR", {}).get("bme680_sda_pin"))
bme_scl_pin = int(config.get("SENSOR", {}).get("bme680_scl_pin"))
ldr_pin = int(config.get("SENSOR", {}).get("ldr_pin", 34))
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
ESP_NOW_KEY = config.get("ESP_NOW", {}).get("esp_key")
if not ESP_NOW_KEY:
    ESP_NOW_KEY = b'\x00' * 16  # Default key if not set
    print("[ESP_NOW] Using default ESP-NOW key.")

BUFFER = []
BUFFER_FILE = "buffer.txt"
MAX_FAILURES = 3

# === Sensor Setup ===
print("[SENSOR] Setting up sensors...")
ldr = None
if use_ldr:
    try:
        ldr = ADC(Pin(ldr_pin))
        ldr.atten(ADC.ATTN_11DB)
        print(f"[SENSOR] LDR sensor initialized on pin {ldr_pin}.")
    except Exception as e:
        print(f"[SENSOR] Failed to initialize LDR on pin {ldr_pin}: {e}")

bme = None
if use_bme:
    try:
        i2c = I2C(scl=Pin(bme_scl_pin), sda=Pin(bme_sda_pin))
        bme = BME680_I2C(i2c=i2c)
        print(f"[SENSOR] BME680 sensor initialized on SDA={bme_sda_pin}, SCL={bme_scl_pin}.")
    except Exception as e:
        print(f"[SENSOR] Failed to initialize BME680 on SDA={bme_sda_pin}, SCL={bme_scl_pin}: {e}")

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

    device_id = sta.config('mac').hex()
    print(f"[GATEWAY] Device ID: {device_id}")
    partial_msgs = {}  # node_id: { "total": int, "parts": {idx: bytes}, "start": ticks_ms }
    TIMEOUT_MS = 30000  # 30 seconds
    last_sensor_time = time.ticks_ms()
    last_kpi_time = time.ticks_ms()

    while True:
        if not sta.isconnected():
            print("[GATEWAY] Wi-Fi lost. Resetting...")
            time.sleep(2)
            machine.reset()

        host, msg = esp.recv()

        # Send KPI
        if time.ticks_diff(time.ticks_ms(), last_kpi_time) > 60000:
            kpi_msg = f"KPI|device_id={device_id};uptime={time.ticks_ms() // 1000}"
            print(f"[GATEWAY] Sending KPI: {kpi_msg}")
            try:
                client.publish(f"mesh/kpi/esp-gateway", kpi_msg)
            except Exception as e:
                print(f"[GATEWAY] Failed to send KPI: {e}")
            last_kpi_time = time.ticks_ms()

        if msg:
            node_id = host.hex()
            now = time.ticks_ms()

            if msg == b"DISCOVER_GATEWAY":
                mac = sta.config('mac')
                print(f"[GATEWAY] Responding to DISCOVER_GATEWAY from {host}")
                esp.send(host, b"I_AM_GATEWAY:" + mac)

            elif msg.startswith(b"PART[") and b"]|" in msg:
                try:
                    header_end = msg.index(b"]|") + 2
                    header = msg[:header_end].decode()
                    body = msg[header_end:]

                    part_info = header[5:-2]
                    idx, total = map(int, part_info.split("/"))

                    if node_id not in partial_msgs:
                        partial_msgs[node_id] = {
                            "total": total,
                            "parts": {},
                            "start": now
                        }

                    partial_msgs[node_id]["parts"][idx] = body
                    print(f"[GATEWAY] Received part {idx}/{total} from {node_id}")

                    if len(partial_msgs[node_id]["parts"]) == total:
                        parts = partial_msgs[node_id]["parts"]
                        full_msg = b''.join([parts[i] for i in range(1, total + 1)])
                        topic = f"mesh/data/{node_id}"
                        print(f"[GATEWAY] Reconstructed full message from {node_id}: {full_msg}")
                        client.publish(topic, full_msg)
                        del partial_msgs[node_id]

                except Exception as e:
                    print(f"[GATEWAY] Failed to process multipart message: {e}")
            elif msg.startswith(b"KPI|"):
                    topic = f"mesh/kpi/{node_id}"
                    kpi_data = msg[4:]  # Strip prefix "KPI|"
                    print(f"[GATEWAY] KPI from {node_id}: {kpi_data}")
                    client.publish(topic, kpi_data)
                    continue
            else:
                topic = f"mesh/data/{node_id}"
                print(f"[GATEWAY] MQTT publish from node {node_id}: {msg}")
                client.publish(topic, msg)

        # Timeout cleanup for incomplete messages
        now = time.ticks_ms()
        expired = []
        for nid in partial_msgs:
            if time.ticks_diff(now, partial_msgs[nid]["start"]) > TIMEOUT_MS:
                expired.append(nid)
        for nid in expired:
            print(f"[GATEWAY] Dropping incomplete message from {nid} due to timeout.")
            del partial_msgs[nid]

        # Own sensor reading
        if time.ticks_diff(time.ticks_ms(), last_sensor_time) > sensor_read_interval:
            payload = read_sensors()
            if payload:
                topic = "mesh/data/{device_id}"
                print(f"[GATEWAY] MQTT publish (own sensor): {payload}")
                client.publish(topic, payload)
            last_sensor_time = time.ticks_ms()

        time.sleep(0.1)

def node_loop():
    gateway_mac = None
    print("[NODE] I am NODE. Discovering gateway...")

    BUFFER[:] = load_buffer()
    consecutive_failures = 0

    # KPI variables
    kpi_readings = 0
    kpi_sent = 0
    kpi_failures = 0
    last_kpi_time = time.ticks_ms()

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
        if time.ticks_diff(time.ticks_ms(), last_read) >= sensor_read_interval:
            payload = read_sensors()
            if payload:
                kpi_readings += 1
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
                kpi_sent += 1
            except Exception as e:
                print(f"[NODE] Send failed: {e}")
                consecutive_failures += 1
                kpi_failures += 1
                if consecutive_failures >= MAX_FAILURES:
                    print("[NODE] Lost connection to gateway. Resetting discovery.")
                    gateway_mac = None
                break

        BUFFER[:] = BUFFER[i:]
        save_buffer(BUFFER)

        # === Send KPIs ===
        if time.ticks_diff(time.ticks_ms(), last_kpi_time) >= kpi_interval:
            uptime = time.ticks_ms() // 1000
            kpi_msg = f"KPI|readings={kpi_readings};sent={kpi_sent};failures={kpi_failures};uptime={uptime}"
            print(f"[NODE] Sending KPI: {kpi_msg}")
            try:
                esp.send(gateway_mac, kpi_msg.encode())
            except Exception as e:
                print(f"[NODE] Failed to send KPI: {e}")
            last_kpi_time = time.ticks_ms()

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