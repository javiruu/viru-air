"""Shared deeplink URL builders for door-to-door providers.

Builders are honest — no fake durations, no fake prices, no fake availability.
All URLs open external services; Viru does not confirm price, schedule, or availability.
"""

from urllib.parse import urlencode, quote

from app.door_to_door.schemas import DoorToDoorActionOut


# ── Airport city mapping (shared) ────────────────────────────────
_AIRPORT_CITY: dict[str, str] = {
    "AGP": "Málaga",
    "MAD": "Madrid",
    "BCN": "Barcelona",
    "ALC": "Alicante",
    "VLC": "Valencia",
    "SVQ": "Sevilla",
    "BIO": "Bilbao",
    "PMI": "Palma de Mallorca",
    "GRO": "Girona",
    "REU": "Reus",
    "ZAZ": "Zaragoza",
    "GRX": "Granada",
    "LEI": "Almería",
    "TSF": "Treviso",
    "VCE": "Venecia",
    "FCO": "Roma",
    "MXP": "Milán",
    "BGY": "Bérgamo",
    "ORY": "París",
    "CDG": "París",
    "LGW": "Londres",
    "STN": "Londres",
    "LTN": "Londres",
    "AMS": "Ámsterdam",
    "BRU": "Bruselas",
    "CRL": "Charleroi",
}


def airport_city(iata: str) -> str:
    """Return the city name for an airport IATA code, or the IATA itself if unknown."""
    return _AIRPORT_CITY.get(iata.upper(), iata)


def airport_label(iata: str) -> str:
    """Return a human-readable airport label like 'Aeropuerto de Málaga AGP'."""
    city = airport_city(iata)
    if city != iata:
        return f"Aeropuerto de {city} {iata}"
    return f"Aeropuerto de {iata}"


# ── Known BlaBlaCar place ids ────────────────────────────────────
_BLABLACAR_PLACE_ID_BY_LABEL: dict[str, str] = {
    "almería, españa": "eyJpIjoiQ2hJSndmTE03QUNlZWcwUlhraThqaC1nblkwIiwicCI6MSwidiI6MSwidCI6WzRdfQ==",
    "alicante, españa": "eyJpIjoiQ2hJSlM2dWRPOW8xWWcwUjQ0RUxySEtvZlIwIiwicCI6MSwidiI6MSwidCI6WzRdfQ==",
    "málaga, españa": "eyJpIjoiQ2hJSkxTSGJUOFJaY2cwUnp6TEt5WkxjSldBIiwicCI6MSwidiI6MSwidCI6WzRdfQ==",
    "sevilla, españa": "eyJpIjoiQ2hJSmtXSy1GQkZzRWcwUlNGYi1IR0lZOERRIiwicCI6MSwidiI6MSwidCI6WzRdfQ==",
    "madrid, españa": "eyJpIjoiQ2hJSmdUd0tnSmNwUWcwUmFTS01ZY0hlTnNRIiwicCI6MSwidiI6MSwidCI6WzRdfQ==",
    "aeroport josep tarradellas barcelona-el prat (bcn), el prat de llobregat, españa": "eyJpIjoiQ2hJSnBZNThoR1NlcEJJUjE1dHYtMExwS19NIiwicCI6MSwidiI6MSwidCI6WzJdfQ==",
}

_BLABLACAR_PLACE_ID_BY_IATA: dict[str, str] = {
    "AGP": _BLABLACAR_PLACE_ID_BY_LABEL["málaga, españa"],
    "ALC": _BLABLACAR_PLACE_ID_BY_LABEL["alicante, españa"],
    "SVQ": _BLABLACAR_PLACE_ID_BY_LABEL["sevilla, españa"],
    "MAD": _BLABLACAR_PLACE_ID_BY_LABEL["madrid, españa"],
    "BCN": _BLABLACAR_PLACE_ID_BY_LABEL["aeroport josep tarradellas barcelona-el prat (bcn), el prat de llobregat, españa"],
}


def _resolve_blablacar_place_id(label: str | None, iata: str | None) -> str | None:
    """Try to resolve a BlaBlaCar place_id from label text or IATA code."""
    if iata:
        pid = _BLABLACAR_PLACE_ID_BY_IATA.get(iata.upper())
        if pid:
            return pid
    if label:
        normalized = " ".join(label.strip().lower().split())
        pid = _BLABLACAR_PLACE_ID_BY_LABEL.get(normalized)
        if pid:
            return pid
    return None


# ── Builders ─────────────────────────────────────────────────────

def build_google_maps_action(
    origin_label: str,
    destination_label: str,
    action_id: str,
    *,
    origin_coords: tuple[float, float] | None = None,
    destination_coords: tuple[float, float] | None = None,
) -> DoorToDoorActionOut:
    """Build a Google Maps directions deeplink.

    Uses coordinates (lat,lng) when available for precise navigation.
    Falls back to text labels when coordinates are missing.
    """
    if origin_coords:
        origin_param = f"{origin_coords[0]},{origin_coords[1]}"
    else:
        origin_param = quote(origin_label)

    if destination_coords:
        dest_param = f"{destination_coords[0]},{destination_coords[1]}"
    else:
        dest_param = quote(destination_label)

    url = (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={origin_param}"
        f"&destination={dest_param}"
        f"&travelmode=driving"
        f"&dir_action=navigate"
    )
    return DoorToDoorActionOut(
        id=action_id,
        provider="google_maps",
        label="Abrir en Google Maps",
        url=url,
        kind="directions",
        opens_external=True,
        source_status="external_search",
        price_status="external",
        availability_status="external",
        trust_copy="Precio, horario y plazas se confirman fuera de Viru.",
    )


def build_blablacar_action(
    from_name: str,
    to_name: str,
    date_str: str,
    passengers: int,
    action_id: str,
    *,
    from_place_id: str | None = None,
    to_place_id: str | None = None,
    from_iata: str | None = None,
    to_iata: str | None = None,
) -> DoorToDoorActionOut:
    """Build a BlaBlaCar search deeplink.

    Uses place_ids when available for precise search.
    Falls back to text-based search when place_ids are missing.
    """
    params: dict[str, str] = {
        "search_origin": "SEARCH",
        "p0[ac]": "adult",
        "fn": from_name,
        "tn": to_name,
        "db": date_str,
        "seats": str(max(1, passengers)),
    }

    # Resolve place_ids: explicit params first, then auto-resolve
    resolved_from = from_place_id or _resolve_blablacar_place_id(from_name, from_iata)
    resolved_to = to_place_id or _resolve_blablacar_place_id(to_name, to_iata)

    if resolved_from:
        params["from_place_id"] = resolved_from
    if resolved_to:
        params["to_place_id"] = resolved_to

    url = f"https://www.blablacar.es/search?{urlencode(params)}"
    return DoorToDoorActionOut(
        id=action_id,
        provider="blablacar",
        label="Buscar en BlaBlaCar",
        url=url,
        kind="provider_search",
        opens_external=True,
        source_status="external_search",
        price_status="external",
        availability_status="external",
        trust_copy="Precio, horario y plazas se confirman fuera de Viru.",
    )


def build_goopti_action(
    pickup: str,
    dropoff: str,
    date_str: str,
    passengers: int,
    action_id: str,
) -> DoorToDoorActionOut:
    """Build a GoOpti shuttle search deeplink."""
    params: dict[str, str] = {
        "pickup": pickup,
        "dropoff": dropoff,
        "date": date_str,
    }
    if passengers > 1:
        params["passengers"] = str(passengers)

    url = f"https://www.goopti.com/es/?{urlencode(params)}"
    return DoorToDoorActionOut(
        id=action_id,
        provider="goopti",
        label="Buscar traslado en GoOpti",
        url=url,
        kind="provider_search",
        opens_external=True,
        source_status="external_search",
        price_status="external",
        availability_status="external",
        trust_copy="Precio, horario y plazas se confirman fuera de Viru.",
    )
