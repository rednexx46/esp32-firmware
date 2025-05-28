Here is your updated `README.md` reflecting all current features and improvements from the latest version of the code:

---

# ESP32 Mesh Sensor Network

A robust and flexible ESP32-based mesh sensor network using **ESP-NOW** and **MQTT**, built with **MicroPython**. Devices dynamically assume roles as **nodes** or a **gateway**, support multiple sensors, KPI reporting, and buffered delivery.

---

## 🚀 Features

* 🧠 **Auto Role Detection**: Devices auto-detect if they are gateway or node
* 📡 **ESP-NOW Mesh**: Nodes send data to gateway via low-power ESP-NOW
* 🌐 **Wi-Fi + MQTT**: Gateway connects to broker and publishes data
* 🌡️ **Sensor Support**: BME680 (temp, humidity, pressure) and LDR (light)
* 📊 **KPI Reporting**:

  * Nodes send KPIs (readings, sent, failures, uptime)
  * Gateway sends uptime KPIs
  * KPIs are sent via MQTT under `mesh/kpi/<device_id>`
* 💾 **Buffered Delivery**: Sensor data is stored and resent if gateway is offline
* 🔒 **Shared ESP-NOW Key** for security
* 🔧 **Full Config via `config.ini`**

---

## 🧱 Architecture

```text
[NODEs] --(ESP-NOW)--> [GATEWAY] --(MQTT)--> [BROKER]
                                      │
                      ┌───────────────┴───────────────┐
                      ▼                               ▼
             mesh/data/<device_id>         mesh/kpi/<device_id>
```

---

## 🗂️ File Structure

| File                    | Description                              |
| ----------------------- | ---------------------------------------- |
| `main.py`               | Device logic (role, sensors, comms, KPI) |
| `boot.py`               | Wi-Fi and config initialization          |
| `config_reader.py`      | Parses `config.ini` into Python dict     |
| `bme680.py`             | Driver for BME680 sensor via I2C         |
| `config.ini`            | Configuration file                       |
| `flash-mpy-tutorial.md` | How to flash MicroPython onto your ESP32 |

---

## ⚙️ Configuration (`config.ini`)

```ini
[KPI]
kpi_interval = 60

[ESP_NOW]
esp_key = msh1234567890esp

[WIFI]
wifi_ssid = ESPMeshAP
wifi_password = OwsLmJh9ENdDTaW

[MQTT]
mqtt_broker = broker.local
mqtt_port = 1883
mqtt_user = esp-gateway
mqtt_password = F6mwB6AEe08Bvt6

[SENSOR]
use_bme680 = false
bme_sda_pin = 21
bme_scl_pin = 22
use_ldr = true
ldr_pin = 34
sensor_read_interval = 30
```

---

## 📦 MQTT Topics

| Topic                   | Description                    |
| ----------------------- | ------------------------------ |
| `mesh/data/<device_id>` | Sensor data from nodes/gateway |
| `mesh/kpi/<device_id>`  | KPIs from each device          |

---

## 📈 Example KPI Messages

From a node:

```
KPI|readings=5;sent=5;failures=0;uptime=120
```

From gateway:

```
KPI|device_id=c0ffeeabcd1234;uptime=300
```

---

## ⚡ Quick Start

1. **Flash MicroPython**
   Follow `flash-mpy-tutorial.md` to flash the firmware.

2. **Configure**
   Edit `config.ini` with your Wi-Fi, MQTT and sensor settings.

3. **Upload Code**
   Use Thonny, ampy, rshell or WebREPL to transfer all `.py` files and `config.ini`.

4. **Power Up**
   Device will boot and auto-select its role:

   * **Gateway**: Publishes data and KPIs to MQTT
   * **Node**: Sends sensor data and KPIs to gateway

---

## 🔐 Security Tips

* Always define a strong `esp_key` in `[ESP_NOW]`
* Use authentication in your MQTT broker (`[MQTT]`)
* Avoid storing sensitive credentials in plain-text for production
