#!/usr/bin/env python3
# manager_flask.py
import os
import signal
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from flask import Flask, jsonify, request, Response

PROJECT_DIR = Path(__file__).parent.resolve()
BOT_SCRIPT = PROJECT_DIR / "bot.py"
LOG_FILE = PROJECT_DIR / "bot_process.log"
RESTART_ON_CRASH = True
RESTART_DELAY = 5  # segundos antes de reintentar

app = Flask(__name__)

# Estado global protegido por lock
_process_lock = threading.Lock()
_process: Optional[subprocess.Popen] = None
_last_start_time: Optional[str] = None
_last_exit_code: Optional[int] = None


def _start_process():
    global _process, _last_start_time, _last_exit_code
    with _process_lock:
        if _process and _process.poll() is None:
            return {"status": "already_running", "pid": _process.pid}
        # abrir el log en modo append
        lf = open(LOG_FILE, "a", buffering=1, encoding="utf-8")
        cmd = [os.environ.get("PYTHON_EXECUTABLE", "python3"), str(BOT_SCRIPT)]
        # iniciar el proceso
        _process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_DIR),
            stdout=lf,
            stderr=subprocess.STDOUT,
            env=os.environ.copy(),
            text=True,
        )
        _last_start_time = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        _last_exit_code = None
        return {"status": "started", "pid": _process.pid, "started_at": _last_start_time}


def _stop_process(graceful: bool = True, timeout: int = 10):
    global _process, _last_exit_code
    with _process_lock:
        if not _process or _process.poll() is not None:
            return {"status": "not_running"}
        try:
            if graceful:
                # intentar terminar suavemente
                _process.terminate()
            else:
                _process.kill()
            try:
                _process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _process.kill()
                _process.wait(timeout=5)
            _last_exit_code = _process.returncode
            return {"status": "stopped", "exit_code": _last_exit_code}
        finally:
            _process = None


def _monitor_loop():
    global _process, _last_exit_code
    while True:
        with _process_lock:
            proc = _process
        if proc:
            ret = proc.poll()
            if ret is not None:
                _last_exit_code = ret
                with _process_lock:
                    _process = None
                # escribir en log que terminó
                with open(LOG_FILE, "a", encoding="utf-8") as lf:
                    lf.write(f"\n[{datetime.utcnow().isoformat(timespec='seconds')}Z] PROCESS EXITED code={ret}\n\n")
                if RESTART_ON_CRASH:
                    time.sleep(RESTART_DELAY)
                    _start_process()
        else:
            # si no hay proceso y RESTART_ON_CRASH es True, intentar arrancar
            if RESTART_ON_CRASH:
                _start_process()
        time.sleep(1)


@app.route("/start", methods=["POST"])
def http_start():
    res = _start_process()
    return jsonify(res)


@app.route("/stop", methods=["POST"])
def http_stop():
    graceful = request.args.get("graceful", "1") != "0"
    res = _stop_process(graceful=graceful)
    return jsonify(res)


@app.route("/restart", methods=["POST"])
def http_restart():
    _stop_process(graceful=True)
    time.sleep(1)
    res = _start_process()
    return jsonify(res)


@app.route("/status", methods=["GET"])
def http_status():
    with _process_lock:
        running = bool(_process and _process.poll() is None)
        pid = _process.pid if _process and _process.poll() is None else None
    return jsonify({
        "running": running,
        "pid": pid,
        "last_start": _last_start_time,
        "last_exit_code": _last_exit_code,
        "log_file": str(LOG_FILE),
    })


@app.route("/logs", methods=["GET"])
def http_logs():
    """Devuelve las últimas N líneas del log. ?lines=200"""
    lines = int(request.args.get("lines", "200"))
    if not LOG_FILE.exists():
        return Response("No hay log todavía.\n", mimetype="text/plain")
    # leer desde el final de forma eficiente
    with open(LOG_FILE, "rb") as f:
        try:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            size = 0
            block = 1024
            data = bytearray()
            while end > 0 and size < lines * 200:  # heurística
                read_size = min(block, end)
                f.seek(end - read_size)
                chunk = f.read(read_size)
                data[:0] = chunk
                end -= read_size
                size += read_size
            text = data.decode("utf-8", errors="replace")
        except Exception:
            f.seek(0)
            text = f.read().decode("utf-8", errors="replace")
    # devolver solo las últimas `lines` líneas
    all_lines = text.splitlines()
    return Response("\n".join(all_lines[-lines:]) + "\n", mimetype="text/plain")


if __name__ == "__main__":
    # arrancar monitor en hilo daemon
    monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    monitor_thread.start()
    # arrancar proceso inmediatamente al iniciar el manager
    _start_process()
    # ejecutar Flask (en producción usa gunicorn / systemd)
    app.run(host="0.0.0.0", port=int(os.environ.get("MANAGER_PORT", "8000")))

