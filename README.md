# ESP32 Mesh Sensor Network

A flexible mesh sensor network using ESP32 devices running MicroPython. Devices can act as either a **gateway** (publishing sensor data to MQTT) or a **node** (sending sensor data to the gateway using ESP-NOW). All configuration is managed via a simple `config.ini` file.

---

## 🚀 Features

- **Mesh Networking:** Uses ESP-NOW for low-power, peer-to-peer communication between nodes and the gateway.
- **Wi-Fi & MQTT:** Gateway connects to Wi-Fi and publishes sensor data to an MQTT broker.
- **Sensor Support:** Supports BME680 (temperature, humidity, pressure, gas) and LDR (light) sensors.
- **Buffering:** Nodes buffer sensor data if the gateway is unavailable and resend when reconnected.
- **Auto Role Selection:** Devices automatically determine if they should act as a gateway or node.
- **Configurable:** All settings (Wi-Fi, MQTT, ESP-NOW key, sensors) are managed in `config.ini`.

---

## 📁 File Structure

| File                   | Description                                                        |
|------------------------|--------------------------------------------------------------------|
| `main.py`              | Main application logic. Handles role selection, sensor reading, and communication. |
| `boot.py`              | Initializes Wi-Fi, ESP-NOW, and loads configuration at boot.        |
| `config_reader.py`     | Loads and parses the `config.ini` file.                             |
| `bme680.py`            | Driver for the BME680 sensor (I2C).                                 |
| `config.ini`           | Project configuration file (Wi-Fi, MQTT, ESP-NOW, sensors).         |
| `flash-mpy-tutorial.md`| Step-by-step guide to flashing MicroPython firmware on ESP32.       |

---

## ⚡ Quick Start

1. **Flash MicroPython**  
    See [`flash-mpy-tutorial.md`](flash-mpy-tutorial.md) for detailed instructions.

2. **Configure**  
    Edit `config.ini` to set your Wi-Fi, MQTT, ESP-NOW key, and sensor options.

3. **Deploy Code**  
    Copy all `.py` files and `config.ini` to your ESP32 using Thonny, ampy, or similar tools.

4. **Power Up**  
    The device will boot, load configuration, and determine its role:
    - **Gateway:** Connects to Wi-Fi and MQTT, listens for nodes, and publishes sensor data.
    - **Node:** Discovers the gateway via ESP-NOW and sends sensor data.

---

## 🛠️ Customization

- **Add/Remove Sensors:** Change `[SENSOR]` section in `config.ini`.
- **Change MQTT Broker:** Update `[MQTT]` section.
- **Change ESP-NOW Key:** Update `[ESP_NOW]` section (must match on all devices).

---

## 📦 Requirements

- ESP32 board
- MicroPython firmware ([download here](https://micropython.org/download/esp32/))
- Python tools: Thonny, esptool (for flashing)

---

## 📚 Documentation

- [`flash-mpy-tutorial.md`](docs/flash-mpy-tutorial.md): How to flash MicroPython on ESP32.

---

## 📄 License

See original sources for sensor drivers. Project code is provided as-is for educational purposes.