@echo off
set PORT=COM5

echo 🚀 Deploying files to ESP32 using ampy...

set FILES=^
boot.py ^
main.py ^
config.ini ^
core\gateway.py ^
core\node.py ^
core\sensor.py ^
network\espnow_comm.py ^
network\wifi_utils.py ^
utils\buffer_utils.py ^
utils\config_reader.py ^
utils\mqtt_utils.py ^
lib\bme680.py

for %%F in (%FILES%) do (
    echo 📤 Uploading %%F...
    ampy --port %PORT% put %%F
)

echo ✅ Deployment finished.
pause