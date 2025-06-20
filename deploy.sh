#!/bin/bash
# NODE01 /dev/cu.usbserial-0001
# NODE02 /dev/tty.SLAB_USBtoUART
# GATEWAY /dev/cu.wchusbserial110
PORT=/dev/cu.usbserial-0001
CLEAR_BEFORE_UPLOAD=true

FILES=(
  boot.py
  main.py
  config.ini
  ble/ble_server.py
  ble/command_handler.py
  core/gateway.py
  core/node.py
  core/sensor.py
  lib/bme680.py
  esp_network/espnow_comm.py
  esp_network/role_selector.py
  esp_network/wifi_utils.py
  utils/buffer_utils.py
  utils/config_reader.py
  utils/config_utils.py
  utils/mqtt_utils.py
)

echo "🚀 Deploying files to ESP32 using ampy..."

if [ "$CLEAR_BEFORE_UPLOAD" = true ]; then
  echo "⚠️  Deleting all files from ESP32..."
  # Remove everything at once (if possible)
  ampy --port $PORT rmdir / 2>/dev/null
fi

# Create all necessary directories at once
echo "📂 Creating directories..."
DIRS=$(for file in "${FILES[@]}"; do dirname "$file"; done | sort -u | grep -v '^.$')
for dir in $DIRS; do
  ampy --port $PORT mkdir "/$dir" 2>/dev/null
done

for file in "${FILES[@]}"; do
  echo "📤 Uploading $file..."
  ampy --port $PORT put "$file" "/$file"
done

echo "✅ Deployment finished."
