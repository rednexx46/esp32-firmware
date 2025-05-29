import time
from core.sensor import read_sensors
from utils.buffer_utils import load_buffer, save_buffer

MAX_FAILURES = 3

def node_loop(config, esp, sta, ldr, bme):
    gateway_mac = None
    BUFFER = load_buffer()

    consecutive_failures = 0
    kpi_readings = 0
    kpi_sent = 0
    kpi_failures = 0
    last_kpi_time = time.ticks_ms()
    last_read = time.ticks_ms()

    def recv_with_timeout(timeout_ms=3000):
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            host, msg = esp.recv()
            if msg:
                return host, msg
            time.sleep(0.05)
        return None, None

    def discover_gateway():
        nonlocal gateway_mac
        esp.send(b'\xff' * 6, b"DISCOVER_GATEWAY")
        host, msg = recv_with_timeout()
        if msg and msg.startswith(b"I_AM_GATEWAY:"):
            gateway_mac = msg.split(b":")[1]
            esp.add_peer(gateway_mac, lmk=config["esp_key"].encode())
            print(f"[NODE] Found gateway: {gateway_mac}")
            return True
        return False

    def send_payload(payload):
        MAX_SIZE = 240
        if len(payload) <= MAX_SIZE:
            esp.send(gateway_mac, payload)
        else:
            parts = [payload[i:i + MAX_SIZE] for i in range(0, len(payload), MAX_SIZE)]
            for idx, part in enumerate(parts):
                header = f"PART[{idx + 1}/{len(parts)}]|".encode()
                esp.send(gateway_mac, header + part)
                time.sleep(0.05)

    print("[NODE] Starting node loop...")
    while True:
        if time.ticks_diff(time.ticks_ms(), last_read) >= config["sensor_read_interval"]:
            payload = read_sensors(ldr, bme)
            if payload:
                kpi_readings += 1
                if len(BUFFER) < 20:
                    BUFFER.append(payload)
                    save_buffer(BUFFER)
                else:
                    print("[NODE] Buffer full.")
            last_read = time.ticks_ms()

        if not gateway_mac:
            if not discover_gateway():
                print("[NODE] No gateway. Retrying...")
                time.sleep(5)
                continue

        i = 0
        while i < len(BUFFER):
            try:
                send_payload(BUFFER[i])
                print(f"[NODE] Sent: {BUFFER[i]}")
                i += 1
                consecutive_failures = 0
                kpi_sent += 1
            except Exception as e:
                print(f"[NODE] Send failed: {e}")
                consecutive_failures += 1
                kpi_failures += 1
                if consecutive_failures >= MAX_FAILURES:
                    print("[NODE] Lost gateway. Rediscovering...")
                    gateway_mac = None
                break

        BUFFER[:] = BUFFER[i:]
        save_buffer(BUFFER)

        if time.ticks_diff(time.ticks_ms(), last_kpi_time) >= config["kpi_interval"]:
            uptime = time.ticks_ms() // 1000
            kpi_msg = f"KPI|readings={kpi_readings};sent={kpi_sent};failures={kpi_failures};uptime={uptime}"
            print(f"[NODE] KPI: {kpi_msg}")
            try:
                esp.send(gateway_mac, kpi_msg.encode())
            except Exception as e:
                print(f"[NODE] Failed to send KPI: {e}")
            last_kpi_time = time.ticks_ms()

        time.sleep(1)