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
* 🛠️ **Modular Codebase**: Cleanly organized by functionality
* 🔧 **Full Config via `config.ini`**
* ⚙️ **Cross-platform Deployment Scripts**: `deploy.sh` (Unix) and `deploy.bat` (Windows)

---

## 🧱 Architecture

```text
[NODEs] --(ESP-NOW)--> [GATEWAY] --(MQTT)--> [BROKER]
                                      │
                      ┌───────────────┴───────────────┐
                      ▼                               ▼
             mesh/data/<device_id>         mesh/kpi/<device_id>
````

---

## 🗂️ Project Structure

```
ESP32-FIRMWARE/
├── boot.py                  # Initializes Wi-Fi and ESP-NOW
├── main.py                  # Determines role and starts logic
├── config.ini               # Configuration file
├── requirements.txt         # Host Python dependencies (e.g. ampy)
├── .gitignore               # Ignore local/temp files
├── deploy.sh                # Deployment script for Linux/macOS
├── deploy.bat               # Deployment script for Windows
├── README.md                # Project documentation

├── core/                    # Core logic
│   ├── gateway.py           # Gateway loop
│   ├── node.py              # Node loop
│   └── sensor.py            # Sensor reading and setup

├── network/                 # Communication layer
│   ├── espnow_comm.py       # Shared ESP-NOW and Wi-Fi state
│   └── wifi_utils.py        # Wi-Fi connection management

├── utils/                   # Support utilities
│   ├── buffer_utils.py      # Persistent message buffering
│   ├── config_reader.py     # Config parsing
│   └── mqtt_utils.py        # MQTT connection checker

├── lib/                     # Hardware libraries
│   └── bme680.py            # BME680 sensor driver

└── docs/
    └── flash-mpy-tutorial.md  # Flashing MicroPython guide
```

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
   Follow `docs/flash-mpy-tutorial.md` to flash firmware to your ESP32.

2. **Edit Configuration**
   Adjust `config.ini` with your network, MQTT, and sensor settings.

3. **Install Tools**
   Install dependencies on your PC:

   ```bash
   pip install -r requirements.txt
   ```

4. **Deploy the Code**

   * On **Linux/macOS**:

     ```bash
     ./deploy.sh
     ```
   * On **Windows**: Run `deploy.bat`

5. **Power the Device**
   On boot, the device:

   * Connects to Wi-Fi
   * Initializes ESP-NOW
   * Automatically becomes a **Gateway** or **Node**

---

## 🔐 Security Tips

* Always set a secure, 16-byte `esp_key` in `[ESP_NOW]`
* Use MQTT authentication (`[MQTT]`) with strong passwords
* Avoid storing sensitive credentials in plain text on production devices
