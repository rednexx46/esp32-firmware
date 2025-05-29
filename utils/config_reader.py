from configparser import ConfigParser

def load_config():
    parser = ConfigParser()
    parser.read("config.ini")
    return parser

def setup_config():
    config = load_config()

    # Flatten useful values
    return {
        "kpi_interval": int(config.get("KPI", "kpi_interval", fallback="60")) * 1000,
        "sensor_read_interval": int(config.get("SENSOR", "sensor_read_interval", fallback="30")) * 1000,
        "use_bme680": config.get("SENSOR", "use_bme680", fallback="false").lower() == "true",
        "bme_sda_pin": int(config.get("SENSOR", "bme680_sda_pin", fallback="21")),
        "bme_scl_pin": int(config.get("SENSOR", "bme680_scl_pin", fallback="22")),
        "use_ldr": config.get("SENSOR", "use_ldr", fallback="false").lower() == "true",
        "ldr_pin": int(config.get("SENSOR", "ldr_pin", fallback="34")),
        "mqtt": {
            "host": config.get("MQTT", "mqtt_broker", fallback="broker.local"),
            "port": int(config.get("MQTT", "mqtt_port", fallback="1883")),
            "user": config.get("MQTT", "mqtt_user", fallback=None),
            "pass": config.get("MQTT", "mqtt_password", fallback=None)
        },
        "esp_key": config.get("ESP_NOW", "esp_key", fallback=None)
    }