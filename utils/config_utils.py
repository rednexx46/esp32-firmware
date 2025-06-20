from json import loads, dumps

CONFIG_PATH = "config.ini"

def override_config(payload: str) -> bool:
    try:
        data = loads(payload)
        with open(CONFIG_PATH, "w") as f:
            f.write(dumps(data))
        print("[CONFIG] Config overridden.")
        return True
    except Exception as e:
        print(f"[CONFIG] Failed to override: {e}")
        return False

def get_device_info(sta) -> str:
    try:
        mac = sta.config("mac").hex()
        ip = sta.ifconfig()[0]
        return f"MAC={mac}, IP={ip}"
    except Exception as e:
        return f"Error retrieving device info: {e}"