#!/usr/bin/env bash
# ============================================================
# install_raspi.sh - Instalación de EcoSort AI en Raspberry Pi
# (Raspberry Pi OS 64-bit recomendado). Ejecutar desde la carpeta del proyecto:
#     bash install_raspi.sh
# ============================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_USER="${SUDO_USER:-$USER}"
SERVICE_NAME="ecosort"

echo "==> [1/5] Instalando dependencias del sistema..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip python3-dev \
    libopenblas-dev libjpeg-dev libatlas-base-dev v4l-utils git || \
sudo apt-get install -y python3 python3-venv python3-pip python3-dev \
    libopenblas-dev libjpeg-dev v4l-utils git   # fallback si libatlas ya no existe

echo "==> [2/5] Creando entorno virtual en ${PROJECT_DIR}/venv ..."
python3 -m venv "${PROJECT_DIR}/venv"

echo "==> [3/5] Instalando requirements (puede tardar varios minutos)..."
"${PROJECT_DIR}/venv/bin/pip" install --upgrade pip
"${PROJECT_DIR}/venv/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"

echo "==> [4/5] Permisos de cámara y GPIO para el usuario ${RUN_USER}..."
sudo usermod -aG video,gpio "${RUN_USER}" || true

echo "==> [5/5] Configurando arranque automático con systemd..."
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null <<EOF
[Unit]
Description=EcoSort AI - Controlador de contenedores
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/venv/bin/python ${PROJECT_DIR}/raspi_controller.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.service"
echo
echo "Instalación completa."
echo "  1) Copia tu modelo exportado a: ${PROJECT_DIR}/models/best_ncnn_model/"
echo "  2) Inicia el servicio:  sudo systemctl start ${SERVICE_NAME}"
echo "  3) Ver logs:            journalctl -u ${SERVICE_NAME} -f"
echo "  4) Reinicia sesión para aplicar los grupos video/gpio."
