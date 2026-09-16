#!/usr/bin/env bash
# Instalación en Raspberry Pi OS (Bookworm o posterior).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Paquetes del sistema =="
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-picamera2 alsa-utils libgl1 libatlas-base-dev i2c-tools
sudo raspi-config nonint do_i2c 0 || echo "Activa I2C a mano con raspi-config si usas el PCA9685"

echo "== Entorno virtual (con acceso a picamera2 del sistema) =="
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e ".[opencv,gpio]"

read -r -p "¿Instalar YOLO (ultralytics)? Recomendado en Pi 4/5 [s/N] " yn
if [[ "${yn:-n}" =~ ^[sS]$ ]]; then
  pip install -e ".[yolo]"
  echo "Exportando modelo a NCNN para la Pi (puede tardar unos minutos)..."
  yolo export model=yolov8n.pt format=ncnn imgsz=320 || echo "Exportación fallida; se usará yolov8n.pt"
fi

echo "== Sonidos =="
python scripts/make_sounds.py

if [[ ! -f config.yaml ]]; then
  cp config.example.yaml config.yaml
  echo "Creado config.yaml a partir del ejemplo; edítalo antes de arrancar."
fi

echo "== Servicios systemd =="
for unit in fuera-gatos.service fuera-gatos@.service; do
  sed "s|__DIR__|$(pwd)|g; s|__USER__|$(whoami)|g" "systemd/$unit" | sudo tee "/etc/systemd/system/$unit" >/dev/null
done
sudo systemctl daemon-reload
echo
echo "Una sola cámara (config.yaml):"
echo "  sudo systemctl enable --now fuera-gatos"
echo "Varias cámaras (config.frente.yaml, config.fondo.yaml):"
echo "  cp examples/config.frente.yaml config.frente.yaml && cp examples/config.fondo.yaml config.fondo.yaml"
echo "  sudo systemctl enable --now fuera-gatos@frente fuera-gatos@fondo"
echo "Registro:  journalctl -u 'fuera-gatos*' -f"
