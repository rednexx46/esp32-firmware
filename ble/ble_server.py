from ubluetooth import BLE, UUID, FLAG_WRITE, FLAG_NOTIFY
from ble.command_handler import handle_command

_ADV_PAYLOAD = b'\x02\x01\x06\x03\x03\x9e\xfe'  # Simplified BLE advertising

class BLEServer:
    def __init__(self, sta):
        self.sta = sta
        self.ble = BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)

        self.connections = set()

        # Nordic UART Service UUIDs (16-bit compatible with mobile BLE tools)
        self._svc_uuid = UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
        self._cmd_uuid = UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")   # Write
        self._resp_uuid = UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")  # Notify

        services = (
            (self._svc_uuid, (
                (self._cmd_uuid, FLAG_WRITE),
                (self._resp_uuid, FLAG_NOTIFY),
            )),
        )

        ((self.cmd_handle, self.resp_handle),) = self.ble.gatts_register_services(services)
        self._advertise()

    def _advertise(self):
        self.ble.gap_advertise(100, _ADV_PAYLOAD)
        print("[BLE] Advertising...")

    def _irq(self, event, data):
        if event == 1:  # Central connected
            conn_handle = data[0]
            self.connections.add(conn_handle)
            print("[BLE] Connected")
        elif event == 2:  # Central disconnected
            conn_handle = data[0]
            self.connections.discard(conn_handle)
            print("[BLE] Disconnected")
            self._advertise()
        elif event == 3:  # Write to characteristic
            conn_handle, attr_handle = data
            if attr_handle == self.cmd_handle:
                try:
                    command = self.ble.gatts_read(attr_handle).decode()
                    response = handle_command(command, self.sta)
                    self.ble.gatts_notify(conn_handle, self.resp_handle, response.encode())
                except Exception as e:
                    print(f"[BLE] Command error: {e}")

    def stop(self):
        try:
            self.ble.gap_advertise(None)  # Stop advertising
            self.ble.active(False)        # Deactivate BLE radio
            self.connections.clear()
            print("[BLE] Stopped BLE server.")
        except Exception as e:
            print(f"[BLE] Error while stopping BLE server: {e}")