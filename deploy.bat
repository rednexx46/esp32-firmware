@echo off
REM NODE01 COM5
REM NODE02 COM6
REM GATEWAY COM7
set PORT=COM5
set CLEAR_BEFORE_UPLOAD=true

REM Lista de arquivos para upload
set FILES=boot.py main.py config.ini ble\ble_server.py ble\command_handler.py core\gateway.py core\node.py core\sensor.py lib\bme680.py esp_network\espnow_comm.py esp_network\role_selector.py esp_network\wifi_utils.py utils\buffer_utils.py utils\config_reader.py utils\config_utils.py utils\mqtt_utils.py

echo 🚀 Deploying files to ESP32 using ampy...

if /i "%CLEAR_BEFORE_UPLOAD%"=="true" (
    echo ⚠️  Deleting all files from ESP32...
    ampy --port %PORT% rmdir / 2>nul
)

REM Criar diretórios necessários
echo 📂 Creating directories...
setlocal enabledelayedexpansion
for %%F in (%FILES%) do (
    set "FILE=%%F"
    for %%D in ("!FILE:\=" "!") do (
        set "DIR=%%~dpD"
        set "DIR=!DIR:/=\!"
        if not "!DIR!"=="" (
            set "DIR=!DIR:~0,-1!"
            if not "!DIR!"=="." (
                if not exist "!DIR!" (
                    ampy --port %PORT% mkdir "/!DIR!" 2>nul
                )
            )
        )
    )
)

REM Upload dos arquivos
for %%F in (%FILES%) do (
    echo 📤 Uploading %%F...
    ampy --port %PORT% put %%F /%%F
)

endlocal

echo ✅ Deployment finished.
pause