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
            print("[SENSOR] BME680 initialized on pin SCL={} SDA={}".format(config["bme_scl_pin"], config["bme_sda_pin"]))
        except Exception as e:
            print(f"[SENSOR] Failed to init BME680: {e}")

    return ldr, bme

def read_sensors(ldr, bme):
    ldr_value = None
    bme_data = None

    if ldr:
        try:
            ldr_value = ldr.read()
            print(f"[SENSOR] LDR: {ldr_value}")
        except Exception as e:
            print(f"[SENSOR] Failed to read LDR: {e}")

    if bme:
        try:
            # Adafruit MicroPython BME680 reads directly
            t = round(bme.temperature, 2)
            h = round(bme.humidity, 2)
            p = round(bme.pressure, 2)
            bme_data = (t, h, p)
            print(f"[SENSOR] BME: T={t}C H={h}% P={p}hPa")
        except Exception as e:
            print(f"[SENSOR] Failed to read BME680: {e}")

    if ldr_value is not None and bme_data is not None:
        t, h, p = bme_data
        return f"LDR={ldr_value} T={t}C H={h}% P={p}hPa".encode()
    elif ldr_value is not None:
        return f"LDR={ldr_value}".encode()
    elif bme_data is not None:
        t, h, p = bme_data
        return f"T={t}C H={h}% P={p}hPa".encode()
    else:
        return b"no_data"