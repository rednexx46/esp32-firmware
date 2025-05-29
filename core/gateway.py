import time
import machine
from umqtt.simple import MQTTClient
from core.sensor import read_sensors

def gateway_loop(config, esp, sta, ldr, bme):
    print("[GATEWAY] Starting gateway loop...")
    mqtt_cfg = config["mqtt"]
    client = MQTTClient("gateway", mqtt_cfg["host"], port=mqtt_cfg["port"], user=mqtt_cfg["user"], password=mqtt_cfg["pass"])
    client.connect()

    device_id = sta.config('mac').hex()
    partial_msgs = {}
    TIMEOUT_MS = 30000
    last_sensor_time = time.ticks_ms()
    last_kpi_time = time.ticks_ms()

    while True:
        if not sta.isconnected():
            print("[GATEWAY] Wi-Fi lost. Resetting...")
            time.sleep(2)
            machine.reset()

        host, msg = esp.recv()

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
                print(f"[GATEWAY] Responding to discovery from {host}")
                esp.send(host, b"I_AM_GATEWAY:" + mac)

            elif msg.startswith(b"PART[") and b"]|" in msg:
                try:
                    header_end = msg.index(b"]|") + 2
                    header = msg[:header_end].decode()
                    body = msg[header_end:]
                    idx, total = map(int, header[5:-2].split("/"))

                    if node_id not in partial_msgs:
                        partial_msgs[node_id] = {"total": total, "parts": {}, "start": now}

                    partial_msgs[node_id]["parts"][idx] = body
                    print(f"[GATEWAY] Received part {idx}/{total} from {node_id}")

                    if len(partial_msgs[node_id]["parts"]) == total:
                        parts = partial_msgs[node_id]["parts"]
                        full_msg = b''.join([parts[i] for i in range(1, total + 1)])
                        client.publish(f"mesh/data/{node_id}", full_msg)
                        del partial_msgs[node_id]

                except Exception as e:
                    print(f"[GATEWAY] Error processing multipart: {e}")

            elif msg.startswith(b"KPI|"):
                client.publish(f"mesh/kpi/{node_id}", msg[4:])
            else:
                client.publish(f"mesh/data/{node_id}", msg)

        # Timeout cleanup
        now = time.ticks_ms()
        expired = [nid for nid in partial_msgs if time.ticks_diff(now, partial_msgs[nid]["start"]) > TIMEOUT_MS]
        for nid in expired:
            print(f"[GATEWAY] Dropping incomplete msg from {nid}")
            del partial_msgs[nid]

        # Own sensor data
        if time.ticks_diff(time.ticks_ms(), last_sensor_time) > config["sensor_read_interval"]:
            payload = read_sensors(ldr, bme)
            if payload:
                client.publish(f"mesh/data/{device_id}", payload)
            last_sensor_time = time.ticks_ms()

        time.sleep(0.1)