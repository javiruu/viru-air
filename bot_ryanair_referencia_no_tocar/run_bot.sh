#!/bin/bash
set -e

PROJECT_DIR="/bot_ryanair"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE="ryanairbot.service"

case "$1" in
  start)
    echo "🚀 Iniciando bot + panel web..."
    systemctl start $SERVICE
    ;;
  stop)
    echo "🛑 Deteniendo bot..."
    systemctl stop $SERVICE
    ;;
  restart)
    echo "🔄 Reiniciando servicio..."
    systemctl restart $SERVICE
    ;;
  status)
    systemctl status $SERVICE
    ;;
  tail)
    echo "📜 Mostrando logs (Ctrl+C para salir)..."
    journalctl -u $SERVICE -f
    ;;
  manual)
    echo "⚙️ Ejecutando manualmente sin systemd (modo desarrollo)..."
    source "$VENV_DIR/bin/activate"
    python3 "$PROJECT_DIR/main.py"
    ;;
  *)
    echo "Uso: ./run_bot.sh {start|stop|restart|status|tail|manual}"
    exit 1
    ;;
esac
