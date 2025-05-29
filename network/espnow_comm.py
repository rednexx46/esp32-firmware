_sta = None
_esp = None
_wifi_status = False

def set_sta(sta_obj):
    global _sta
    _sta = sta_obj

def get_sta():
    return _sta

def set_esp(esp_obj):
    global _esp
    _esp = esp_obj

def get_esp():
    return _esp

def set_wifi_status(status):
    global _wifi_status
    _wifi_status = status

def get_wifi_status():
    return _wifi_status