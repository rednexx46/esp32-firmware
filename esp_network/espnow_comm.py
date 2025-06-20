esp_instance = None
esp_role = None
sta_instance = None

def set_esp(esp):
    """Set the global ESP-NOW instance."""
    global esp_instance
    esp_instance = esp

def get_esp():
    """Get the global ESP-NOW instance."""
    return esp_instance

def set_role(role):
    """Set the role of the ESP-NOW instance."""
    global esp_role
    esp_role = role

def get_role():
    """Get the role of the ESP-NOW instance."""
    return esp_role

def set_sta(sta):
    """Set the global Wi-Fi STA instance."""
    global sta_instance
    sta_instance = sta

def get_sta():
    """Get the global Wi-Fi STA instance."""
    return sta_instance

def reset_globals():
    """Reset all global variables used in ESP-NOW communication."""
    global esp_instance, sta_instance, esp_role
    esp_instance = None
    sta_instance = None
    esp_role = None
    print("[ESP-NOW] Globals reset.")
