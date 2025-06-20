from time import ticks_ms, ticks_diff, sleep
from core.sensor import read_sensors
from utils.buffer_utils import load_buffer, save_buffer
from esp_network.espnow_comm import get_role
from _thread import start_new_thread

MAX_PAYLOAD_SIZE = 240
MAX_BUFFER_SIZE = 20

# Globals
known_peers = {}  # {mac: (role, last_seen_ms)}

def start_node_beacon(esp, beacon_interval):
    def beacon_loop():
        print("[ROLE] Starting I_AM_NODE beacon loop.")
        while get_role() == "node":
            try:
                # Sends a beacon if is a node or if any peer is a gateway
                if any(role == "gateway" for role, _ in known_peers.values()):
                    esp.send(b'\xff' * 6, b"I_AM_NODE")
            except Exception as e:
                print(f"[ROLE] Node beacon error: {e}")
            sleep(beacon_interval)
        print("[ROLE] Stopping I_AM_NODE beacon loop.")
    start_new_thread(beacon_loop, ())

def scan_peers(esp, esp_key):
    """Broadcast a discovery message and collect active peers with roles."""
    global known_peers
    known_peers.clear()

    print("[NODE] Broadcasting peer discovery...")
    esp.send(b'\xff' * 6, b"DISCOVER_GATEWAY")

    start = ticks_ms()
    while ticks_diff(ticks_ms(), start) < 3000:
        host, msg = esp.recv()

        if not msg or not isinstance(host, bytes) or len(host) != 6:
            continue

        try:
            role = None
            if msg.startswith(b"I_AM_GATEWAY"):
                role = "gateway"
                print(f"[NODE] Detected gateway: {host.hex()}")
            elif msg.startswith(b"I_AM_NODE"):
                role = "node"
                print(f"[NODE] Detected node: {host.hex()}")
            else:
                continue

            if role:
                if host not in known_peers:
                    esp.add_peer(host, lmk=esp_key)
                known_peers[host] = (role, ticks_ms())

        except Exception as e:
            print(f"[NODE] Failed to process peer {host.hex()}: {e}")

    return bool(known_peers)


def send_payload(esp, payload, target, origin_mac):
    """Send a payload directly or forward it if needed."""

    if not isinstance(target, bytes) or len(target) != 6:
        print("[NODE] Invalid target MAC address.")
        return

    try:
        if len(payload) <= MAX_PAYLOAD_SIZE:
            msg = b"FORWARD|" + origin_mac.hex().encode() + b"|" + payload
            print(f"[NODE] Sending payload to {target.hex()}: {msg}")
            esp.send(target, msg)
        else:
            parts = [payload[i:i + MAX_PAYLOAD_SIZE] for i in range(0, len(payload), MAX_PAYLOAD_SIZE)]
            for idx, part in enumerate(parts):
                header = f"PART[{idx + 1}/{len(parts)}]|".encode()
                msg = b"FORWARD|" + origin_mac.hex().encode() + b"|" + header + part
                esp.send(target, msg)
                sleep(0.05)
    except Exception as e:
        print(f"[NODE] Failed to send payload to {target.hex()}: {e}")


def process_kpi(esp, target, stats, origin_mac):
    """Send KPI metrics to a selected peer."""
    kpi = f"KPI|readings={stats['readings']};sent={stats['sent']};failures={stats['failures']};uptime={stats['uptime']}"
    try:
        send_payload(esp, kpi.encode(), target, origin_mac)
    except Exception as e:
        print(f"[NODE] Failed to send KPI: {e}")


def prune_known_peers(esp, peer_timeout_ms):
    """Remove peers that haven’t responded recently."""
    now = ticks_ms()
    expired = [mac for mac, (_, last_seen) in known_peers.items() if ticks_diff(now, last_seen) > peer_timeout_ms]
    for mac in expired:
        try:
            esp.del_peer(mac)
            print(f"[NODE] Removing inactive peer: {mac.hex()}")
            del known_peers[mac]
        except Exception as e:
            print(f"[NODE] Failed to remove peer {mac.hex()}: {e}")

def get_best_target():
    """Select the best target peer for sending messages."""
    # Try gateway first
    for mac, (role, _) in known_peers.items():
        if role == "gateway":
            return mac
    # Otherwise, fallback to most recently seen peer
    if known_peers:
        return max(known_peers.items(), key=lambda x: x[1][1])[0]
    return None

def node_loop(config, esp, sta, ldr, bme):
    """Main loop for the node role."""
    buffer = load_buffer()
    stats = {"readings": 0, "sent": 0, "failures": 0, "uptime": 0}
    consecutive_failures = 0
    last_kpi_time = ticks_ms()
    last_read = ticks_ms()
    origin_mac = sta.config("mac")
    retries = 0

    print("[NODE] Entering main loop...")

    PEER_TIMEOUT_MS = config.get("peer_timeout")
    SENSOR_READ_INTERVAL = config.get("sensor_read_interval")
    MAX_SEND_FAILURES = config.get("max_failures", 3)
    KPI_INTERVAL = config["kpi_interval"]

    while True:
        now = ticks_ms()

        # Listen for incoming messages
        host, msg = esp.recv()
        if msg and isinstance(host, bytes) and len(host) == 6:
            try:
                if msg.startswith(b"I_AM_GATEWAY"):
                    if host not in known_peers:
                        esp.add_peer(host, lmk=config["esp_key"].encode())
                    known_peers[host] = ("gateway", now)
                    print(f"[NODE] Updated gateway peer: {host.hex()}")

                elif msg.startswith(b"I_AM_NODE"):
                    if host not in known_peers:
                        esp.add_peer(host, lmk=config["esp_key"].encode())
                    known_peers[host] = ("node", now)
                    print(f"[NODE] Updated node peer: {host.hex()}")

                elif msg.startswith(b"FORWARD|"):
                    try:
                        _, origin, payload = msg.split(b"|", 2)
                        target = get_best_target()
                        if target:
                            send_payload(esp, payload, target, origin)
                        else:
                            print("[NODE] No known peers to forward message.")
                    except Exception as e:
                        print(f"[NODE] Failed to forward message: {e}")

                elif msg.startswith(b"KPI|"):
                    try:
                        target = get_best_target()
                        if target:
                            process_kpi(esp, target, stats, origin_mac)
                            print(f"[NODE] Forwarded KPI from {host.hex()} to {target.hex()}")
                        else:
                            print("[NODE] No peer available to forward KPI.")
                    except Exception as e:
                        print(f"[NODE] Failed to forward KPI: {e}")

            except Exception as e:
                print(f"[NODE] Failed to handle incoming message: {e}")

        # If no peers are known, rescan
        if not known_peers:
            found = scan_peers(esp, config["esp_key"].encode())
            if retries >= MAX_SEND_FAILURES:
                print("[NODE] Too many retries without finding peers. Resetting...")
                return
                
            if not found:
                print("[NODE] No peers found.")
                sleep(5)
                retries += 1
                continue
        else:
            retries = 0

        # Periodic sensor reading
        if ticks_diff(now, last_read) >= SENSOR_READ_INTERVAL:
            print(f"[NODE] Reading sensors at {now} ms...")

            try:
                payload = read_sensors(ldr, bme)
            except Exception as e:
                print(f"[NODE] Sensor read error: {e}")
                payload = None

            if payload:
                stats["readings"] += 1
                if len(buffer) >= MAX_BUFFER_SIZE:
                    print(f"[NODE] buffer full. Removing oldest entry.")
                    buffer.pop(0)
                buffer.append(payload)
                save_buffer(buffer)
                print(f"[NODE] Buffered sensor data. Current size: {len(buffer)}")

            last_read = now

        # Try sending buffered data
        i = 0
        while i < len(buffer):
            payload = buffer[i]
            if not isinstance(payload, bytes):
                payload = str(payload).encode()

            try:
                target = get_best_target()
                if not target:
                    raise Exception("No known peers available")
                send_payload(esp, payload, target, origin_mac)
                i += 1
                consecutive_failures = 0
                stats["sent"] += 1
            except Exception as e:
                print(f"[NODE] Failed to send payload: {e}")
                consecutive_failures += 1
                stats["failures"] += 1

                if consecutive_failures >= MAX_SEND_FAILURES:
                    print("[NODE] Max consecutive failures reached. Resetting peers...")
                    known_peers.clear()
                    break

        # Remove sent data from buffer
        buffer[:] = buffer[i:]
        save_buffer(buffer)

        # Periodic KPI reporting
        if ticks_diff(now, last_kpi_time) >= KPI_INTERVAL:
            stats["uptime"] = now // 1000
            try:
                target = get_best_target()
                if target:
                    process_kpi(esp, target, stats, origin_mac)
                    print(f"[NODE] Sent KPI to {target.hex()} from node {origin_mac.hex()}")
            except Exception as e:
                print(f"[NODE] Could not send KPI: {e}")
            last_kpi_time = now

        prune_known_peers(esp, PEER_TIMEOUT_MS)
        sleep(1)