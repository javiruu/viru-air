#!/usr/bin/env python3
# ryanair_api.py

import logging
import requests
from datetime import datetime
from ryanair import Ryanair

# --- Configuración de logging ---
logging.basicConfig(
    format="%(asctime)s - [RYANAIR_API] - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("ryanair_api")

# Inicializar la API oficial de Ryanair
api = Ryanair(currency="EUR")  # Puedes cambiar la moneda si quieres (GBP, HRK, etc.)

# ======================================================
# Método principal para obtener vuelos más baratos
# ======================================================
def fetch_cheapest_price_oneway(origin: str, destination: str, date_str: str):
    """
    Busca el vuelo más barato disponible en la fecha indicada.
    Retorna un diccionario con precio, número de vuelo y hora de salida.
    """
    date = datetime.fromisoformat(date_str).date()
    try:
        flights = api.get_cheapest_flights(origin, date, date)  # rango de 1 día
    except Exception as e:
        logger.error(f"❌ Error al consultar la API ryanair-py: {e}")
        return None

    for f in flights:
        if getattr(f, "destination", "").upper() == destination.upper():
            logger.info(f"✅ Vuelo encontrado: {origin}->{destination} ({date_str}) → {f.price}€")
            return {
                "price": float(f.price),
                "flightNumber": getattr(f, "flightNumber", None),
                "departureTime": getattr(f, "departureTime", None)
            }

    logger.warning(f"⚠️ No se encontró ningún vuelo de {origin} a {destination} el {date_str}")
    return None

# ======================================================
# Método de fallback directo a la API pública de Ryanair
# ======================================================
def get_price(origin: str, destination: str, date: str):
    """
    Consulta la API pública de Ryanair si la librería principal falla.
    Devuelve el precio en euros (float) o None si no hay resultados.
    """
    try:
        url = (
            f"https://www.ryanair.com/api/farfnd/3/oneWayFares"
            f"?&departureAirportIataCode={origin}"
            f"&arrivalAirportIataCode={destination}"
            f"&outboundDepartureDateFrom={date}"
            f"&outboundDepartureDateTo={date}"
        )
        response = requests.get(url, timeout=10)
        data = response.json()

        if "fares" in data and data["fares"]:
            price = data["fares"][0]["outbound"]["price"]["value"]
            logger.info(f"💰 Precio (fallback) {origin}->{destination} ({date}) = {price}€")
            return float(price)

        logger.warning(f"⚠️ No se encontraron precios para {origin}-{destination} {date}")
        return None

    except Exception as e:
        logger.error(f"Error consultando la API pública de Ryanair: {e}")
        return None


# ======================================================
# Uso combinado (inteligente)
# ======================================================
def get_best_price(origin: str, destination: str, date: str):
    """
    Intenta primero con la API oficial (ryanair-py),
    si falla, usa el fallback público.
    """
    result = fetch_cheapest_price_oneway(origin, destination, date)
    if result and "price" in result:
        return result["price"]

    # Fallback si la API no devuelve nada
    return get_price(origin, destination, date)
