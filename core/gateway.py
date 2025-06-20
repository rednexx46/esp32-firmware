from time import ticks_ms, ticks_diff, sleep
from core.sensor import read_sensors
from utils.mqtt_utils import setup_mqtt, safe_publish
from json import dumps
from esp_network.espnow_comm import get_role, set_role
from _thread import start_new_thread

known_peers = set()
mesh_nodes = {}
partial_msgs = {}

def start_gateway_beacon(esp, rssi, beacon_interval):
    def beacon_loop():
        print("[ROLE] Starting I_AM_GATEWAY beacon loop.")
        while get_role() == "gateway":
            try:
                esp.send(b'\xff' * 6, f"I_AM_GATEWAY|{rssi}".encode())
                sleep(beacon_interval)
            except Exception as e:
                print(f"[ROLE] Beacon error: {e}")
                sleep(beacon_interval)
        print("[ROLE] Stopping I_AM_GATEWAY beacon loop.")
    start_new_thread(beacon_loop, ())

def update_node(mac, kpi=None, via="direct"):
    """Update or add a mesh node with its last seen time and optional KPI data."""
    mac_hex = mac.hex()
    now = ticks_ms()
    node = mesh_nodes.get(mac_hex, {})
    node["last_seen"] = now
    node["via"] = via
    if kpi:
        node["kpi"] = kpi
    mesh_nodes[mac_hex] = node

def prune_nodes(esp, node_timeout):
    """Remove nodes that have not been seen for a specified timeout period."""
    now = ticks_ms()
    inactive = [mac for mac, n in mesh_nodes.items() if ticks_diff(now, n["last_seen"]) > node_timeout]
    for mac in inactive:
        try:
            esp.del_peer(mac)
            print(f"[GATEWAY] Node {mac} timed out.")
            del mesh_nodes[mac]
        except Exception as e:
            print(f"[GATEWAY] Failed to remove peer {mac.hex()}: {e}")
    global known_peers
    known_peers = {peer for peer in known_peers if peer in mesh_nodes}

def handle_multipart(msg, node_id, client, mqtt, device_id):
    """Handle multipart messages by reassembling them from parts."""
    now = ticks_ms()
    try:
        header_end = msg.index(b"]|") + 2
        header = msg[:header_end].decode()
        body = msg[header_end:]
        idx, total = map(int, header[5:-2].split("/"))
        if node_id not in partial_msgs:
            partial_msgs[node_id] = {"total": total, "parts": {}, "start": now}
        if idx in partial_msgs[node_id]["parts"]:
            return
        partial_msgs[node_id]["parts"][idx] = body
        print(f"[GATEWAY] Received part {idx}/{total} from {node_id}")
        if len(partial_msgs[node_id]["parts"]) == total:
            parts = partial_msgs[node_id]["parts"]
            full_msg = b''.join([parts[i] for i in range(1, total + 1)])
            safe_publish(client, f"mesh/data/{node_id}", full_msg, mqtt, device_id)
            del partial_msgs[node_id]
    except Exception as e:
        print(f"[GATEWAY] Error processing multipart: {e}")

def handle_forwarded(payload, origin_mac, client, mqtt, device_id):
    """Handle forwarded messages by checking their type and publishing them."""
    if payload.startswith(b"PART[") and b"]|" in payload:
        handle_multipart(payload, origin_mac, client, mqtt, device_id)
    elif payload.startswith(b"KPI|"):
        safe_publish(client, f"mesh/kpi/{origin_mac.hex() if isinstance(origin_mac, bytes) else origin_mac}", payload[4:], mqtt, device_id)
    else:
        safe_publish(client, f"mesh/data/{origin_mac.hex() if isinstance(origin_mac, bytes) else origin_mac}", payload, mqtt, device_id)
    print(f"[GATEWAY] Forwarded from {origin_mac.hex() if isinstance(origin_mac, bytes) else origin_mac}: {payload[:50]}")

def process_msg(msg, host, client, esp, esp_key, mqtt, device_id):
    """Process incoming messages from ESP-NOW and handle them accordingly."""
    if not isinstance(msg, bytes) or not host or len(host) != 6:
        print("[GATEWAY] Invalid sender or message type.")
        return
    
    print(f"[GATEWAY] Received message from {host.hex()}: {msg[:50]}...")

    if msg.startswith(b"FORWARD|"):
        try:
            parts = msg.split(b"|", 2)
            if len(parts) == 3:
                origin_mac_str = parts[1].decode()
                origin_mac = bytes.fromhex(origin_mac_str)
                payload = parts[2]
                update_node(origin_mac, via="relay")
                handle_forwarded(payload, origin_mac.hex(), client, mqtt, device_id)
            else:
                print("[GATEWAY] Malformed FORWARD message.")
        except Exception as e:
            print(f"[GATEWAY] Error processing FORWARD message: {e}")
        return
    
    elif msg.startswith(b"I_AM_GATEWAY|"):
        print(f"[GATEWAY] Detected better gateway. Switching to node.")
        set_role("node")
        return

    elif msg == b"I_AM_NODE":
        print(f"[GATEWAY] Received peer announcement from {host.hex()}")
        if host not in known_peers:
            try:
                print(f"[GATEWAY] Adding new peer: {host.hex()}")
                esp.add_peer(host, lmk=esp_key)
            except OSError as e:
                if "ESP_ERR_ESPNOW_EXIST" not in str(e):
                    print(f"[GATEWAY] Error adding peer: {e}")
        update_node(host, via="direct")
        return

    elif msg == b"DISCOVER_GATEWAY":
        try:
            if host not in known_peers:
                try:
                    print(f"[GATEWAY] Adding new peer: {host.hex()}")
                    esp.add_peer(host, lmk=esp_key)
                except OSError as e:
                    if "ESP_ERR_ESPNOW_EXIST" not in str(e):
                        print(f"[GATEWAY] Error adding peer: {e}")
                known_peers.add(host)
            print(f"[GATEWAY] Responding to discovery from {host.hex()}")
        except Exception as e:
            print(f"[GATEWAY] Error responding to discovery: {e}")
        return
    
    elif msg.startswith(b"CANDIDATE|"):
        return

    elif msg.startswith(b"KPI|"):
        try:
            kpi = msg[4:].decode()
            parts = dict(p.split("=") for p in kpi.split(";"))
            for k in parts:
                parts[k] = int(parts[k])
            update_node(host, kpi=parts, via="direct")
            safe_publish(client, f"mesh/kpi/{host.hex()}", msg[4:], mqtt, device_id)
        except Exception as e:
            print(f"[GATEWAY] Invalid KPI message: {e}")

    elif msg.startswith(b"PART[") and b"]|" in msg:
        update_node(host, via="direct")
        handle_multipart(msg, host, client, mqtt, device_id)

    else:
        update_node(host, via="direct")
        safe_publish(client, f"mesh/data/{host.hex()}", msg, mqtt, device_id)

def gateway_loop(config, esp, sta, ldr, bme):
    """Main loop for the gateway, handling incoming messages and publishing data."""
    print("[GATEWAY] Starting gateway loop...")
    device_id = sta.config('mac').hex()
    mqtt = config.get("mqtt", {})
    client = setup_mqtt(mqtt, device_id)

    if client is None:
        print("[GATEWAY] MQTT client setup failed. Exiting gateway loop.")
        return

    last_sensor_time = ticks_ms()
    last_kpi_time = ticks_ms()
    last_status_time = ticks_ms()

    KPI_INTERVAL = int(config.get("kpi_interval"))
    STATUS_INTERVAL = int(config.get("mesh_status_interval"))
    NODE_TIMEOUT = int(config.get("node_timeout"))
    SENSOR_READ_INTERVAL = int(config.get("sensor_read_interval"))
    ESP_KEY = config.get("esp_key", "").encode()
    MQTT_USER = config.get("mqtt", {}).get("user")

    while get_role() == "gateway":

        now = ticks_ms()

        if not sta.isconnected():
            print("[GATEWAY] Wi-Fi lost.")
            sleep(2)
            return

        if ticks_diff(now, last_kpi_time) > KPI_INTERVAL:
            kpi_msg = f"KPI|device_id={device_id};uptime={now // 1000}"
            if not safe_publish(client, f"mesh/kpi/{MQTT_USER}", kpi_msg, mqtt, device_id):
                break
            last_kpi_time = now

        if ticks_diff(now, last_status_time) > STATUS_INTERVAL:
            status = {
                "gateway_id": device_id,
                "nodes": [
                    {"mac": mac, "last_seen": data.get("last_seen"), "rssi": data.get("rssi")}
                    for mac, data in mesh_nodes.items()
                ]
            }
            if not safe_publish(client, "mesh/status", dumps(status), mqtt, device_id):
                break
            last_status_time = now

        prune_nodes(esp, NODE_TIMEOUT)

        host, msg = esp.recv()
        if msg:
            process_msg(msg, host, client, esp, ESP_KEY, mqtt, device_id)
        
        if get_role() != "gateway":
            print("[GATEWAY] Role changed, exiting loop.")
            break

        expired = [nid for nid in partial_msgs if ticks_diff(now, partial_msgs[nid]["start"]) > NODE_TIMEOUT]
        for nid in expired:
            print(f"[GATEWAY] Dropping incomplete msg from {nid}")
            del partial_msgs[nid]

        if ticks_diff(now, last_sensor_time) > SENSOR_READ_INTERVAL:
            payload = read_sensors(ldr, bme)
            if payload:
                if not safe_publish(client, f"mesh/data/{device_id}", payload, mqtt, device_id):
                    break
            last_sensor_time = now

        sleep(0.1)