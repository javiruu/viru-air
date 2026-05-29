from urllib.parse import urlencode, quote
from app.door_to_door.schemas import DoorToDoorActionOut

def build_google_maps_action(origin_label: str, destination_label: str, action_id: str) -> DoorToDoorActionOut:
    url = f"https://www.google.com/maps/dir/?api=1&origin={quote(origin_label)}&destination={quote(destination_label)}&travelmode=driving&dir_action=navigate"
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
        trust_copy="Precio, horario y plazas se confirman fuera de Viru."
    )

def build_blablacar_action(from_name: str, to_name: str, date_str: str, passengers: int, action_id: str) -> DoorToDoorActionOut:
    params = {
        "search_origin": "SEARCH",
        "p0[ac]": "adult",
        "fn": from_name,
        "tn": to_name,
        "db": date_str,
        "seats": str(passengers)
    }
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
        trust_copy="Precio, horario y plazas se confirman fuera de Viru."
    )

def build_goopti_action(pickup: str, dropoff: str, date_str: str, passengers: int, action_id: str) -> DoorToDoorActionOut:
    params = {
        "pickup": pickup,
        "dropoff": dropoff,
        "date": date_str
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
        trust_copy="Precio, horario y plazas se confirman fuera de Viru."
    )
