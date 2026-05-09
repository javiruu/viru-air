#!/usr/bin/env python3
import os
import json
import atexit
import logging
from datetime import datetime

import requests
from flask import (
    Flask, render_template, jsonify, redirect, url_for,
    request, flash, make_response
)
from apscheduler.schedulers.background import BackgroundScheduler
from ryanair_api import get_price  # get_price(origin, destination, date) -> float|None
from scan import quick_scan_liubliana_almeria  # NUEVO: búsqueda rápida ±3 días

# ==============================
# LOGGING
# ==============================
logging.basicConfig(
    format="%(asctime)s - [WEB] - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("web")

# ==============================
# CONFIGURACIÓN BASE
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
I18N_FILE = os.path.join(BASE_DIR, "translations.json")

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)
app.secret_key = os.environ.get("RYANAIR_WEB_SECRET", "change-me")

VUELOS_FILE = os.path.join(BASE_DIR, "vuelos_guardados.json")
HISTORICO_FILE = os.path.join(BASE_DIR, "precios_historicos.json")
LAST_UPDATE_FILE = os.path.join(BASE_DIR, "last_update.txt")

# ==============================
# TELEGRAM ALERTAS
# ==============================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def send_telegram_alert(text: str):
    """Envía mensaje a Telegram usando tu bot."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️ No hay TOKEN o CHAT_ID configurado, no se envía mensaje.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            logger.info("📨 Mensaje Telegram enviado correctamente.")
        else:
            logger.error(f"❌ Error enviando a Telegram: {resp.text}")
    except Exception as e:
        logger.error(f"Error en send_telegram_alert: {e}")


# ==============================
# I18N (traducciones)
# ==============================
def _load_translations():
    try:
        if os.path.exists(I18N_FILE):
            with open(I18N_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        logger.warning("translations.json no encontrado/ inválido, usando claves como fallback.")
    except Exception as e:
        logger.error(f"Error cargando translations.json: {e}")
    return {}


LANGS = _load_translations()


def get_lang():
    code = request.cookies.get("lang")
    if code in LANGS:
        return code
    header = (request.headers.get("Accept-Language") or "").lower()
    return "es" if header.startswith("es") else "en"


@app.route("/lang/<code>")
def set_lang(code):
    if code not in LANGS:
        code = "es"
    resp = make_response(redirect(request.referrer or url_for("home")))
    resp.set_cookie("lang", code, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return resp


@app.context_processor
def inject_i18n():
    lang = get_lang()
    bundle = LANGS.get(lang, LANGS.get("es", {}))

    def t(key, **fmt):
        text = bundle.get(key, key)
        try:
            return text.format(**fmt) if fmt else text
        except Exception:
            return text

    lang_toggle = "en" if lang == "es" else "es"
    return dict(t=t, lang=lang, lang_toggle=lang_toggle)

# ==============================
# HELPERS
# ==============================


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Error leyendo {path}: {e}")
        return []


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error guardando {path}: {e}")
        return False


def set_last_update(ts=None):
    try:
        if ts is None:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
            f.write(ts)
    except Exception as e:
        logger.error(f"Error guardando last update: {e}")


def get_last_update():
    try:
        if os.path.exists(LAST_UPDATE_FILE):
            with open(LAST_UPDATE_FILE, "r", encoding="utf-8") as f:
                return f.read().strip() or "—"
    except Exception:
        pass
    return "—"

# ==============================
# Ventanas / control histórico diario
# ==============================

PRICE_CHANGE_EPS = 0.01     # sensibilidad
AM_START, AM_END = (5, 10)  # 05:00–10:59
PM_START, PM_END = (11, 17)  # 11:00–17:59


def _window_of(dt: datetime) -> str | None:
    h = dt.hour
    if AM_START <= h <= AM_END:
        return "AM"
    if PM_START <= h <= PM_END:
        return "PM"
    return None


def _same_ymd(a_iso: str, b_dt: datetime) -> bool:
    try:
        a = datetime.strptime(a_iso[:19], "%Y-%m-%dT%H:%M:%S")
        return (a.year, a.month, a.day) == (b_dt.year, b_dt.month, b_dt.day)
    except Exception:
        return False


def _find_day_window_index(hist: list, o: str, d: str, flight_date: str,
                           day_dt: datetime, win: str) -> int | None:
    """Índice del registro del mismo vuelo/día/ventana ('AM'/'PM') o None."""
    for i in range(len(hist) - 1, -1, -1):
        h = hist[i]
        if h.get("origin") != o or h.get("destination") != d or h.get("date") != flight_date:
            continue
        checked = h.get("checked_at")
        if not isinstance(checked, str):
            continue
        if _same_ymd(checked, day_dt):
            try:
                t = datetime.strptime(checked[:19], "%Y-%m-%dT%H:%M:%S")
            except Exception:
                continue
            old_win = _window_of(t)
            if old_win == win:
                return i
    return None


def _price_changed(a: float, b: float, eps: float = PRICE_CHANGE_EPS) -> bool:
    return abs(a - b) > eps


def _store_alert_marker_for_flight(vuelos: list, o: str, d: str,
                                   flight_date: str, price: float):
    """Guarda last_alert_at/last_alert_price en vuelos_guardados.json para el vuelo concreto."""
    changed = False
    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    for v in vuelos:
        if v.get("origin") == o and v.get("destination") == d and v.get("date") == flight_date:
            v["last_alert_at"] = now_iso
            v["last_alert_price"] = float(price)
            changed = True
            break
    if changed:
        save_json(VUELOS_FILE, vuelos)


def _can_alert_now(vuelo: dict, price: float, target: float) -> bool:
    """True solo si precio <= target y no se spamea."""
    if price > target:
        return False

    last_price = vuelo.get("last_alert_price")
    last_at = vuelo.get("last_alert_at")
    if last_price is None and last_at is None:
        return True

    try:
        if last_price is not None and float(last_price) > float(target):
            return True
    except Exception:
        pass

    if isinstance(last_at, str):
        try:
            last_dt = datetime.strptime(last_at[:19], "%Y-%m-%dT%H:%M:%S")
            if last_dt.date() == datetime.now().date() and not _price_changed(
                float(last_price or price), float(price)
            ):
                return False
        except Exception:
            pass

    try:
        if last_price is not None and _price_changed(float(last_price), float(price)):
            return True
    except Exception:
        pass

    return last_price is None

# ==============================
# ACTUALIZACIÓN DE PRECIOS (vuelos guardados)
# ==============================


def actualizar_precios_core():
    """
    Para cada vuelo en vuelos_guardados.json guarda como mucho DOS puntos por día:
    - uno en AM (05:00–10:59)
    - uno en PM (11:00–17:59)
    Solo escribe si hay cambio frente al punto guardado en esa ventana.
    Envía alerta si cae por debajo del target (con anti-spam).
    """
    now = datetime.now()
    win = _window_of(now)
    if win is None:
        logger.info("⏭️ Fuera de ventanas (AM/PM). No se guarda histórico en esta ejecución.")
        return 0

    vuelos = load_json(VUELOS_FILE)
    historico = load_json(HISTORICO_FILE)
    cambios = 0

    for vuelo in vuelos:
        try:
            origin = vuelo.get("origin")
            destination = vuelo.get("destination")
            date_str = vuelo.get("date")
            if not (origin and destination and date_str):
                continue

            precio = get_price(origin, destination, date_str)
            if precio is None:
                continue
            precio = float(precio)

            idx = _find_day_window_index(historico, origin, destination, date_str, now, win)

            if idx is not None:
                old_price = float(historico[idx].get("price", precio))
                if _price_changed(old_price, precio):
                    historico[idx] = {
                        "origin": origin,
                        "destination": destination,
                        "date": date_str,
                        "price": precio,
                        "checked_at": now.strftime("%Y-%m-%dT%H:%M:%S")
                    }
                    cambios += 1
                    logger.info(
                        f"✏️ Actualizado {origin}->{destination} {date_str} ({win}) {old_price}→{precio}"
                    )
                else:
                    logger.info(
                        f"🔁 Sin cambios {origin}->{destination} {date_str} ({win}) {old_price}"
                    )
            else:
                historico.append({
                    "origin": origin,
                    "destination": destination,
                    "date": date_str,
                    "price": precio,
                    "checked_at": now.strftime("%Y-%m-%dT%H:%M:%S")
                })
                cambios += 1
                logger.info(f"➕ Guardado {origin}->{destination} {date_str} ({win}) = {precio}")

            target = vuelo.get("target_price")
            if isinstance(target, (int, float)):
                target = float(target)
                if _can_alert_now(vuelo, precio, target):
                    logger.info(
                        f"🔔 Bajo objetivo ({origin}->{destination} {date_str}): {precio} <= {target}"
                    )
                    send_telegram_alert(
                        f"🔔 ¡Precio bajo objetivo!\n\n"
                        f"{origin} → {destination} ({date_str})\n"
                        f"Precio actual: {precio}€ (objetivo: {target}€)"
                    )
                    _store_alert_marker_for_flight(
                        vuelos, origin, destination, date_str, precio
                    )

        except Exception as e:
            logger.error(f"❌ Error actualizando {vuelo}: {e}")

    if cambios > 0:
        save_json(HISTORICO_FILE, historico)
        set_last_update()
        logger.info(f"✅ Cambios aplicados: {cambios} (máx 2 puntos/día por vuelo).")
    else:
        logger.info("⚠️ No se registraron cambios (ventana cubierta y sin variación).")

    return cambios


@app.route("/actualizar")
def actualizar_precios():
    nuevos = actualizar_precios_core()
    t = inject_i18n()["t"]
    if nuevos > 0:
        flash(t("flash_update_ok", n=nuevos), "ok")
    else:
        flash(t("flash_update_warn"), "warn")
    return redirect(url_for("ver_historico"))

# ==============================
# BÚSQUEDA RÁPIDA (usa scan.py)
# ==============================


@app.route("/quick-scan", methods=["GET", "POST"])
def quick_scan_view():
    """
    Lanza la búsqueda rápida ±3 días para las rutas predefinidas (solo Ryanair).
    Toda la lógica pesada está en scan.py::quick_scan_liubliana_almeria.
    """
    results = None
    base_date = ""
    bundle = LANGS.get(get_lang(), {})
    t = (lambda k, **fmt: bundle.get(k, k).format(**fmt) if fmt else bundle.get(k, k))

    if request.method == "POST":
        base_date = (request.form.get("date") or "").strip()
        if not base_date:
            flash("Introduce una fecha.", "error")
        else:
            try:
                results = quick_scan_liubliana_almeria(base_date)
                if not results:
                    msg_tpl = bundle.get("quick_scan_empty",
                                         "No se encontraron vuelos en ±3 días de {date}.")
                    flash(msg_tpl.format(date=base_date), "warn")
            except ValueError as e:
                flash(str(e), "error")
            except Exception as e:
                logger.error(f"Error en quick_scan_view: {e}")
                flash("Error realizando la búsqueda rápida.", "error")

    return render_template("quick_scan.html", results=results, base_date=base_date)

# ==============================
# RUTAS WEB
# ==============================


@app.route("/")
def home():
    vuelos = load_json(VUELOS_FILE)
    historico = load_json(HISTORICO_FILE)
    last_update = get_last_update()
    return render_template(
        "index.html",
        vuelos=vuelos,
        historico=historico,
        last_update=last_update
    )


@app.route("/vuelos")
def lista_vuelos():
    vuelos = load_json(VUELOS_FILE)
    return render_template("vuelos.html", vuelos=vuelos)


@app.route("/historico")
def ver_historico():
    historico = load_json(HISTORICO_FILE)
    routes = sorted({
        f"{e.get('origin','')}|{e.get('destination','')}|{e.get('date','')}"
        for e in historico
        if e.get('origin') and e.get('destination') and e.get('date')
    })
    return render_template("historico.html", historico=historico, routes=routes)


@app.route("/nuevo", methods=["GET", "POST"])
def nuevo_vuelo():
    t = inject_i18n()["t"]

    if request.method == "GET":
        return render_template("nuevo.html")

    origin = (request.form.get("origin") or "").strip().upper()
    destination = (request.form.get("destination") or "").strip().upper()
    date_str = (request.form.get("date") or "").strip()
    target_raw = (request.form.get("target_price") or "").strip()

    target_price = None
    if target_raw:
        try:
            target_price = float(target_raw.replace(",", "."))
            if target_price < 0:
                raise ValueError
        except ValueError:
            flash("Precio objetivo inválido.", "error")
            return render_template(
                "nuevo.html",
                origin=origin,
                destination=destination,
                date=date_str,
                target_price=target_raw
            ), 400

    errors = []
    if len(origin) != 3:
        errors.append(t("flash_origin_err"))
    if len(destination) != 3:
        errors.append(t("flash_dest_err"))
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        errors.append(t("flash_date_err"))

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template(
            "nuevo.html",
            origin=origin,
            destination=destination,
            date=date_str,
            target_price=target_raw
        ), 400

    vuelos = load_json(VUELOS_FILE)
    if any(
        v.get("origin") == origin
        and v.get("destination") == destination
        and v.get("date") == date_str
        for v in vuelos
    ):
        flash(t("flash_dup_warn"), "warn")
        return redirect(url_for("lista_vuelos"))

    nuevo = {"origin": origin, "destination": destination, "date": date_str}
    if target_price is not None:
        nuevo["target_price"] = target_price

    vuelos.append(nuevo)
    if save_json(VUELOS_FILE, vuelos):
        flash(t("flash_saved_ok"), "ok")
    else:
        flash(t("flash_saved_err"), "error")

    return redirect(url_for("lista_vuelos"))

# ==============================
# API
# ==============================


@app.route("/api/vuelos")
def api_vuelos():
    return jsonify(load_json(VUELOS_FILE))


@app.route("/api/historico")
def api_historico():
    return jsonify(load_json(HISTORICO_FILE))


@app.route("/api/inject_price", methods=["POST"])
def api_inject_price():
    data = request.get_json(force=True) or {}
    origin = data.get("origin")
    destination = data.get("destination")
    date = data.get("date")
    price = data.get("price")

    try:
        price = float(price)
    except (TypeError, ValueError):
        price = None

    if not (origin and destination and date and isinstance(price, float)):
        return jsonify({"message": "Datos incompletos o inválidos"}), 400

    historico = load_json(HISTORICO_FILE)
    historico.append({
        "origin": origin,
        "destination": destination,
        "date": date,
        "price": price,
        "checked_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    })
    save_json(HISTORICO_FILE, historico)
    set_last_update()
    return jsonify({"message": "Precio inyectado correctamente"}), 200


@app.route("/api/delete_price", methods=["POST"])
def api_delete_price():
    data = request.get_json(force=True) or {}
    origin = data.get("origin")
    destination = data.get("destination")
    date = data.get("date")
    checked_at = data.get("checked_at")

    if not (origin and destination and date and checked_at):
        return jsonify({"message": "Datos incompletos"}), 400

    historico = load_json(HISTORICO_FILE)
    idx = next((
        i for i, h in enumerate(historico)
        if h.get("origin") == origin
        and h.get("destination") == destination
        and h.get("date") == date
        and h.get("checked_at") == checked_at
    ), None)

    if idx is None:
        return jsonify({"message": "No se encontró ese registro"}), 404

    del historico[idx]
    save_json(HISTORICO_FILE, historico)
    set_last_update()
    return jsonify({"message": "Registro eliminado correctamente"}), 200


@app.route("/api/calendar")
def api_calendar():
    vuelos = load_json(VUELOS_FILE)
    events = []
    for v in vuelos:
        o = v.get("origin")
        d = v.get("destination")
        dt = v.get("date")
        if not (o and d and dt):
            continue
        events.append({"title": f"{o} → {d}", "start": dt})
    return jsonify(events)

# ==============================
# SCHEDULER
# ==============================

scheduler = None


def start_scheduler():
    global scheduler
    if scheduler is not None:
        return
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        actualizar_precios_core,
        "interval",
        hours=1,
        id="auto_update_prices",
        replace_existing=True
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    logger.info("⏱️ Actualización automática iniciada.")

# ==============================
# ERRORES
# ==============================


@app.errorhandler(404)
def page_not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Ruta API no válida"}), 404
    return redirect(url_for("home"))

# ==============================
# ENTRY POINT
# ==============================

if __name__ == "__main__":
    should_start = (not app.debug) or (os.environ.get("WERKZEUG_RUN_MAIN") == "true")
    if should_start:
        start_scheduler()
    logger.info("🌐 Servidor Flask iniciado en http://0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080, debug=True)
