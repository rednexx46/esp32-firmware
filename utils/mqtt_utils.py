from umqtt.simple import MQTTClient

def can_be_gateway(config):
    try:
        client = MQTTClient("esp32", config["mqtt"]["host"], port=config["mqtt"]["port"],
                            user=config["mqtt"]["user"], password=config["mqtt"]["pass"])
        client.connect()
        client.disconnect()
        print("[MQTT] Broker reachable.")
        return True
    except Exception as e:
        print(f"[MQTT] Connection failed: {e}")
        return False