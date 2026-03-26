#!/usr/bin/env python3
import sys
import os
import asyncio
import logging
import signal
import contextlib

# ==============================
# CONFIGURACIÓN DE LOGGING
# ==============================
logging.basicConfig(
    format="%(asctime)s - [MAIN] - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("MAIN")

# ==============================
# RUTAS BASE
# ==============================
BASE_DIR = "/bot_ryanair"
VENV_PYTHON = os.path.join(BASE_DIR, "venv/bin/python")
BOT_SCRIPT = os.path.join(BASE_DIR, "bot.py")
WEB_SCRIPT = os.path.join(BASE_DIR, "web_app.py")

# ==============================
# PROCESOS ACTIVOS
# ==============================
processes = []

# ==============================
# LANZAR PROCESO HIJO
# ==============================
async def launch_process(cmd, name):
    logger.info(f"🚀 Iniciando {name}: {' '.join(cmd)}")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=BASE_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        processes.append((name, proc))

        async for line in proc.stdout:
            logger.info(f"[{name}] {line.decode(errors='ignore').strip()}")

        await proc.wait()
        logger.warning(f"⚠️ {name} finalizó con código {proc.returncode}")
    except asyncio.CancelledError:
        logger.warning(f"🟡 {name} cancelado manualmente.")
    except Exception as e:
        logger.error(f"❌ Error ejecutando {name}: {e}")

# ==============================
# APAGADO LIMPIO
# ==============================
async def terminate_all():
    """Detiene todos los procesos hijos de forma limpia."""
    for name, proc in processes:
        if proc and proc.returncode is None:
            try:
                logger.info(f"⏹ Terminando {name}...")
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5)
                logger.info(f"✅ {name} cerrado correctamente.")
            except Exception as e:
                logger.error(f"Error cerrando {name}: {e}")

def shutdown(signum=None, frame=None):
    """Handler de señales del sistema."""
    logger.warning(f"🛑 Señal {signum} recibida. Cerrando procesos...")

    try:
        # Ejecutar el cierre limpio dentro de un loop temporal
        asyncio.run(terminate_all())
    except Exception:
        pass  # Evita "Event loop is closed"
    finally:
        logger.info("👋 Todos los procesos finalizados.")
        sys.exit(0)

# ==============================
# MAIN
# ==============================
async def main():
    logger.info("✅ MAIN iniciado. Lanzando servicios...")

    if not os.path.exists(VENV_PYTHON):
        logger.error("❌ No se encontró el entorno virtual en /bot_ryanair/venv")
        sys.exit(1)

    bot_task = asyncio.create_task(launch_process([VENV_PYTHON, BOT_SCRIPT], "BOT"))

    if os.path.exists(WEB_SCRIPT):
        web_task = asyncio.create_task(launch_process([VENV_PYTHON, WEB_SCRIPT], "WEB"))
        await asyncio.gather(bot_task, web_task)
    else:
        logger.warning("🌐 No se encontró web_app.py — solo se ejecutará el BOT.")
        await bot_task

# ==============================
# ENTRY POINT
# ==============================
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        shutdown(signal.SIGINT)
    except Exception as e:
        logger.exception(f"❌ Error fatal en main.py: {e}")
