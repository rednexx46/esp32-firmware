from umqtt.simple import MQTTClient
from esp_network.espnow_comm import set_role

def setup_mqtt(mqtt, device_id):
    if not mqtt or not mqtt.get("host") or not mqtt.get("port") or not mqtt.get("user") or not mqtt.get("pass"):
        print("[GATEWAY] MQTT configuration is incomplete. Cannot connect.")
        return None
    try:
        client = MQTTClient(f"gateway-{device_id}", mqtt["host"], port=mqtt["port"],
                            user=mqtt["user"], password=mqtt["pass"])
        client.connect()
        print("[GATEWAY] Connected to MQTT broker.")
        return client
    except Exception as e:
        print(f"[GATEWAY] Failed to connect to MQTT broker: {e}")
        return None

def safe_publish(client, topic, payload, mqtt, device_id):
    try:
        client.publish(topic, payload)
        return True
    except Exception as e:
        print(f"[GATEWAY] Publish failed on topic '{topic}': {e}")
        try:
            print("[GATEWAY] Attempting MQTT reconnect...")
            new_client = setup_mqtt(mqtt, device_id)
            new_client.publish(topic, payload)
            client.__dict__.update(new_client.__dict__)
            return True
        except Exception as retry_e:
            print(f"[GATEWAY] Retry failed: {retry_e}")
            print("[GATEWAY] Switching role to node due to MQTT failure.")
            set_role("node")
            return False