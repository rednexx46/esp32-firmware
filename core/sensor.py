from machine import ADC, Pin, I2C
from lib.bme680 import BME680_I2C

def setup_sensors(config):
    ldr = None
    bme = None

    if config["use_ldr"]:
        try:
            ldr = ADC(Pin(config["ldr_pin"]))
            ldr.atten(ADC.ATTN_11DB)
            print(f"[SENSOR] LDR initialized on pin {config['ldr_pin']}")
        except Exception as e:
            print(f"[SENSOR] Failed to init LDR: {e}")

    if config["use_bme680"]:
        try:
            i2c = I2C(scl=Pin(config["bme_scl_pin"]), sda=Pin(config["bme_sda_pin"]))
            bme = BME680_I2C(i2c=i2c)
            print("[SENSOR] BME680 initialized.")
        except Exception as e:
            print(f"[SENSOR] Failed to init BME680: {e}")

    return ldr, bme

def read_sensors(ldr, bme):
    if ldr:
        value = ldr.read()
        print(f"[SENSOR] LDR: {value}")
        return f"LDR={value}".encode()

    if bme and bme.get_sensor_data():
        t = round(bme.data.temperature, 2)
        h = round(bme.data.humidity, 2)
        p = round(bme.data.pressure, 2)
        print(f"[SENSOR] BME: T={t}C H={h}% P={p}hPa")
        return f"T={t}C H={h}% P={p}hPa".encode()

    return b"no_data"