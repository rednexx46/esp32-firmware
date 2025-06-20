from machine import reset
from utils.config_utils import override_config, get_device_info

def handle_command(command: str, sta) -> str:
    cmd = command.lower().strip()

    if cmd == "reboot":
        print("[CMD] Reboot requested.")
        reset()
        return "Rebooting..."

    elif cmd.startswith("override|"):
        try:
            print("[CMD] Overriding config.")
            payload = cmd.split("|", 1)[1]
            success = override_config(payload)
            return "Config updated." if success else "Failed to override config."
        except:
            return "Invalid override format."

    elif cmd == "get_info":
        return get_device_info(sta)

    return "Unknown command."