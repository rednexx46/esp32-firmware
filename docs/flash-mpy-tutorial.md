# 🔧 Flashing MicroPython Firmware on ESP32

## 📦 1. Install Required Tools

```bash
pip install thonny esptool
```

> 💡 *Thonny* is optional but recommended as a simple IDE for MicroPython.

---

## 🔄 2. Erase Existing Firmware

1. **Connect your ESP32** via USB.
2. **Hold down the `BOOT` or `FLASH` button** on the ESP32.
3. While holding the button, run:

```bash
esptool --chip esp32 erase_flash
```

> ✅ This clears the current firmware from the device.

---

## ⬇️ 3. Flash MicroPython Firmware

1. Download the latest MicroPython firmware for ESP32 from:
   👉 [https://micropython.org/download/esp32/](https://micropython.org/download/esp32/)

2. Again, **hold down the `BOOT` or `FLASH` button**.

3. Run the following command, replacing `<firmware.bin>` with the path to your downloaded `.bin` file:

```bash
esptool --chip esp32 write_flash -z 0x1000 <firmware.bin>
```

> 📌 The address `0x1000` is the standard starting offset for ESP32.

---

## ✅ 4. Done

* After flashing, you can release the button and **open Thonny**, selecting:

  * **Interpreter** → `MicroPython (ESP32)`
  * **Port** → the serial port of your device (e.g., `COM3` or `/dev/ttyUSB0`)

---
