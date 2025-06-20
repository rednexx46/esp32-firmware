def load_config():
    config = {}
    section = None

    try:
        with open("config.ini") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(";") or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1]
                    config[section] = {}
                elif "=" in line and section:
                    key, value = map(str.strip, line.split("=", 1))
                    config[section][key] = value
    except Exception as e:
        print(f"[CONFIG] Failed to read config.ini: {e}")
        return {}

    return config


def setup_config():
    raw = load_config()
    return {

        # ESP-NOW configuration
        "esp_key": raw.get("ESP_NOW", {}).get("esp_key", "1234567890123456"),

        # Wi-Fi configuration
        "wifi_ssid": raw.get("WIFI", {}).get("wifi_ssid"),
        "wifi_password": raw.get("WIFI", {}).get("wifi_password"),
        "wifi_timeout": int(raw.get("WIFI", {}).get("wifi_timeout", 10)),
        "wifi_channel": int(raw.get("WIFI", {}).get("wifi_channel", 7)),

        # GATEWAY configuration
        "rssi_threshold": int(raw.get("GATEWAY", {}).get("rssi_threshold", -65)),
        "gateway_beacon_interval": int(raw.get("GATEWAY", {}).get("beacon_interval", 5)),
        "mesh_status_interval": int(raw.get("GATEWAY", {}).get("mesh_status_interval", 30)) * 1000,
        "node_timeout": int(raw.get("GATEWAY", {}).get("node_timeout", 60)) * 1000,
        "kpi_interval": int(raw.get("GATEWAY", {}).get("kpi_interval", 30)) * 1000,

        # NODE configuration
        "node_beacon_interval": int(raw.get("NODE", {}).get("beacon_interval", 2)),
        "max_send_failures": int(raw.get("NODE", {}).get("max_send_failures", 3)),
        "gateway_timeout": int(raw.get("NODE", {}).get("gateway_timeout", 30)) * 1000,
        "peer_timeout": int(raw.get("NODE", {}).get("peer_timeout", 60)) * 1000,

        # MQTT configuration
        "mqtt": {
            "host": raw.get("MQTT", {}).get("mqtt_broker", "broker.local"),
            "port": int(raw.get("MQTT", {}).get("mqtt_port", 1883)),
            "user": raw.get("MQTT", {}).get("mqtt_user"),
            "pass": raw.get("MQTT", {}).get("mqtt_password")
        },

        # SENSOR configuration
        "sensor_read_interval": int(raw.get("SENSOR", {}).get("sensor_read_interval", 30)) * 1000,
        "use_bme680": str(raw.get("SENSOR", {}).get("use_bme680", "false")).lower() == "true",
        "bme_sda_pin": int(raw.get("SENSOR", {}).get("bme_sda_pin", 21)),
        "bme_scl_pin": int(raw.get("SENSOR", {}).get("bme_scl_pin", 22)),
        "use_ldr": str(raw.get("SENSOR", {}).get("use_ldr", "false")).lower() == "true",
        "ldr_pin": int(raw.get("SENSOR", {}).get("ldr_pin", 34)),
    }
