#!/bin/bash
set -e

# --- CONFIGURACIÓN ---
PROJECT_DIR="/bot_ryanair"
PYTHON_BIN="python3"
VENV_DIR="$PROJECT_DIR/venv"

echo "============================"
echo "🧩 Configurando entorno para Bot Ryanair + Panel Web"
echo "============================"

# Crear entorno virtual si no existe
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creando entorno virtual..."
    apt update -y
    apt install -y python3 python3-venv python3-pip dos2unix
    $PYTHON_BIN -m venv "$VENV_DIR"
else
    echo "✅ Entorno virtual ya existente."
fi

# Activar entorno virtual
source "$VENV_DIR/bin/activate"

# Instalar dependencias del bot y Flask
echo "📦 Instalando dependencias..."
pip install --upgrade pip
pip install python-telegram-bot[job-queue] flask ryanair-py

# Normalizar finales de línea (por si se copiaron desde Windows)
echo "🔧 Corrigiendo finales de línea..."
dos2unix "$PROJECT_DIR"/setup_bot.sh "$PROJECT_DIR"/run_bot.sh || true

# Dar permisos de ejecución
chmod +x "$PROJECT_DIR"/setup_bot.sh "$PROJECT_DIR"/run_bot.sh

# Crear servicio systemd si no existe
SERVICE_FILE="/etc/systemd/system/ryanairbot.service"

echo "🧠 Creando servicio systemd en $SERVICE_FILE"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Ryanair Bot + Web Panel
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/main.py
Restart=always
User=root
StandardOutput=append:$PROJECT_DIR/bot.log
StandardError=append:$PROJECT_DIR/bot.err

[Install]
WantedBy=multi-user.target
EOF

# Recargar y habilitar servicio
systemctl daemon-reload
systemctl enable ryanairbot.service

echo "============================"
echo "✅ Instalación completa."
echo "Usa:"
echo "  systemctl start ryanairbot   # para arrancar"
echo "  systemctl status ryanairbot  # para ver estado"
echo "  journalctl -u ryanairbot -f  # para logs en vivo"
echo "============================"
