from time import ticks_ms, ticks_diff
from esp_network.espnow_comm import get_role

def elect_role(sta, esp):
    if not sta.isconnected():
        print("[ROLE] Not connected to Wi-Fi. Cannot elect role.")
        return "node"

    mac = sta.config("mac")
    rssi = sta.status("rssi")
    print(f"[ROLE] Electing role... My MAC={mac.hex()} RSSI={rssi}")

    if get_role() != "gateway":
        try:
            esp.send(b'\xff' * 6, f"CANDIDATE|{rssi}".encode())
        except Exception as e:
            print(f"[ROLE] Failed to broadcast candidacy: {e}")
            return "node"

    candidates = {mac: rssi}
    start = ticks_ms()

    print("[ROLE] Listening for candidates (10s)...")
    while ticks_diff(ticks_ms(), start) < 10000:
        try:
            host, msg = esp.recv()
        except:
            continue

        if msg:
            try:
                if msg.startswith(b"CANDIDATE|"):
                    parts = msg.decode().split("|")
                    if len(parts) == 2:
                        _, other_rssi = parts
                        candidates[host] = int(other_rssi)
                        print(f"[ROLE] Candidate from {host.hex()}: RSSI={other_rssi}")
                elif msg.startswith(b"I_AM_GATEWAY|"):
                    parts = msg.decode().split("|")
                    if len(parts) == 2:
                        _, other_rssi = parts
                        candidates[host] = int(other_rssi)
                        print(f"[ROLE] Gateway from {host.hex()}: RSSI={other_rssi}")
            except Exception as e:
                print(f"[ROLE] Parse error: {e}")

    best_mac, best_rssi = max(candidates.items(), key=lambda x: x[1])

    if best_mac == mac:
        print(f"[ROLE] I win (MAC={mac.hex()}, RSSI={rssi}) — I am gateway.")
        return "gateway"
    else:
        print(f"[ROLE] Lost election. Winner: MAC={best_mac.hex()} RSSI={best_rssi}. Acting as node.")
        if get_role() == "gateway":
            print("[ROLE] Stepping down from gateway role.")
        return "node"