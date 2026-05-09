import os
import json
import logging
from datetime import datetime, date as date_cls, timedelta

from ryanair_api import get_price  # misma función que usa el resto del proyecto

logger = logging.getLogger("scan")

# Rutas relevantes (solo Ryanair / alrededores Liubliana ↔ Almería)
QUICK_SCAN_ROUTES = [
    ("TRS", "SVQ"),
    ("TSF", "ALC"),
    ("TSF", "AGP"),
    ("TSF", "SVQ"),
    ("ZAG", "ALC"),
    ("ZAG", "AGP"),
    ("KLU", "ALC"),
    ("VIE", "ALC"),
    ("VIE", "AGP"),
    ("VIE", "MAD"),
    ("VIE", "SVQ"),
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORICO_FILE = os.path.join(BASE_DIR, "precios_historicos.json")
LAST_UPDATE_FILE = os.path.join(BASE_DIR, "last_update.txt")


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"[scan] Error leyendo {path}: {e}")
        return []


def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"[scan] Error guardando {path}: {e}")
        return False


def _set_last_update(ts=None):
    try:
        if ts is None:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
            f.write(ts)
    except Exception as e:
        logger.error(f"[scan] Error guardando last update: {e}")


def quick_scan_liubliana_almeria(base_date_str: str):
    """
    Escanea todas QUICK_SCAN_ROUTES para fecha base ±3 días usando get_price (solo Ryanair).

    - Lee y escribe en precios_historicos.json (mismo formato que el resto):
        {
          "origin": "...",
          "destination": "...",
          "date": "YYYY-MM-DD",
          "checked_at": "YYYY-MM-DDTHH:MM:SS",
          "price": 123.45,
          "currency": "EUR",
          "tag": "quick_scan"
        }

    - Ignora días en el pasado.
    - Devuelve lista de resultados ordenados por precio ascendente.
    """
    try:
        base_date = datetime.strptime(base_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Fecha inválida. Usa formato YYYY-MM-DD.")

    historico = _load_json(HISTORICO_FILE)
    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    results = []

    for origin, destination in QUICK_SCAN_ROUTES:
        for offset in range(-3, 4):  # -3..+3
            d = base_date + timedelta(days=offset)

            # saltar días pasados
            if d < date_cls.today():
                continue

            date_str = d.isoformat()

            try:
                price = get_price(origin, destination, date_str)
            except Exception as e:
                logger.error(
                    f"[scan] Error get_price {origin}->{destination} {date_str}: {e}"
                )
                continue

            if price is None:
                continue

            try:
                price = float(price)
            except (TypeError, ValueError):
                continue

            entry = {
                "origin": origin,
                "destination": destination,
                "date": date_str,
                "price": price,
                "currency": "EUR",
                "checked_at": now_iso,
                "tag": "quick_scan"
            }

            historico.append(entry)
            results.append(entry)

    if results:
        _save_json(HISTORICO_FILE, historico)
        _set_last_update()
        results.sort(key=lambda x: x.get("price", 1e12))
        logger.info(
            f"[scan] Quick-scan {base_date_str}: {len(results)} registros guardados."
        )
    else:
        logger.info(f"[scan] Quick-scan {base_date_str}: sin resultados.")

    return results
