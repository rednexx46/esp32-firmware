#!/bin/bash

# Caminho da porta serial
PORT=/dev/ttyUSB0
FILES=(
  boot.py
  main.py
  config.ini
  core/gateway.py
  core/node.py
  core/sensor.py
  network/espnow_comm.py
  network/wifi_utils.py
  utils/buffer_utils.py
  utils/config_reader.py
  utils/mqtt_utils.py
  lib/bme680.py
)

echo "🚀 Deploying files to ESP32 using ampy..."

for file in "${FILES[@]}"; do
  echo "📤 Uploading $file..."
  ampy --port $PORT put "$file"
done

echo "✅ Deployment finished."