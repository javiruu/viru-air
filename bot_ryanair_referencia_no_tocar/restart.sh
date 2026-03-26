#!/usr/bin/env bash
set -eu

SVC_BOT="ryanair-bot.service"
SVC_WATCHDOG_SERVICE="ryanair-watchdog.service"
SVC_WATCHDOG_TIMER="ryanair-watchdog.timer"

usage() {
  echo "Uso: sudo ./restart.sh [opción]"
  echo "  sin argumentos     Reinicia bot y watchdog"
  echo "  status             Muestra estado de bot, watchdog.timer y watchdog.service"
  echo "  logs               Muestra últimas 50 líneas de logs del bot"
  echo "  enable             Habilita bot y watchdog.timer al arranque"
}

cmd="${1:-run}"

case "$cmd" in
  run)
    echo "↻ Recargando units..."
    systemctl daemon-reload

    echo "↻ Reiniciando $SVC_BOT..."
    systemctl restart "$SVC_BOT"

    echo "↻ Asegurando watchdog.timer habilitado y activo..."
    systemctl enable "$SVC_WATCHDOG_TIMER" >/dev/null 2>&1 || true
    systemctl restart "$SVC_WATCHDOG_TIMER"

    echo "✓ Hecho. Estados:"
    systemctl --no-pager --quiet is-active "$SVC_BOT" && echo "  - $SVC_BOT: active"
    systemctl --no-pager --quiet is-active "$SVC_WATCHDOG_TIMER" && echo "  - $SVC_WATCHDOG_TIMER: active"
    echo
    echo "Sugerencia: ./restart.sh status  |  ./restart.sh logs"
    ;;
  status)
    systemctl status "$SVC_BOT" --no-pager
    echo
    systemctl status "$SVC_WATCHDOG_TIMER" --no-pager || true
    echo
    systemctl status "$SVC_WATCHDOG_SERVICE" --no-pager || true
    ;;
  logs)
    journalctl -u "$SVC_BOT" -n 50 --no-pager
    ;;
  enable)
    systemctl enable "$SVC_BOT"
    systemctl enable "$SVC_WATCHDOG_TIMER"
    systemctl daemon-reload
    echo "✓ Bot y watchdog.timer habilitados al arranque."
    ;;
  *)
    usage
    exit 1
    ;;
esac
