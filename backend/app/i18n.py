"""
Lightweight i18n for backend user-facing strings.

Usage:
    from app.i18n import t

    label = t("es", "hotels.direction.dropped")  # → "bajó"
    label = t("en", "hotels.direction.dropped")  # → "dropped"

    msg = t("es", "hotels.message.price_dropped_to", hotel="Test", currency="EUR", amount="99.00")
    # → "Test: bajó a EUR 99.00"

Default locale is "es" (Spanish-first codebase).
"""

from __future__ import annotations

_STRINGS: dict[str, dict[str, str]] = {
    # ── Notification inbox titles ──
    "notifications.worker_needs_attention": {
        "es": "Worker de señales necesita atención",
        "en": "Signals worker needs attention",
    },
    "notifications.grouped_summary": {
        "es": "Resumen de señales agrupadas",
        "en": "Grouped signals summary",
    },
    "notifications.price_movement": {
        "es": "Movimiento de precio detectado",
        "en": "Price movement detected",
    },
    # ── Hotel alert titles ──
    "hotels.alert.favorable": {
        "es": "Señal hotelera favorable",
        "en": "Favorable hotel signal",
    },
    "hotels.alert.to_watch": {
        "es": "Cambio hotelero a vigilar",
        "en": "Hotel change to watch",
    },
    "hotels.alert.radar_updated": {
        "es": "Radar hotelero actualizado",
        "en": "Hotel radar updated",
    },
    # ── Hotel direction labels ──
    "hotels.direction.dropped": {
        "es": "bajó",
        "en": "dropped",
    },
    "hotels.direction.rose": {
        "es": "subió",
        "en": "rose",
    },
    # ── Hotel alert messages ──
    "hotels.message.sweep_direction": {
        "es": "{hotel}: {direction} de {previous} a {current} {currency} ({pct})",
        "en": "{hotel}: {direction} from {previous} to {current} {currency} ({pct})",
    },
    "hotels.message.price_dropped_to": {
        "es": "{hotel}: bajó a {currency} {amount}",
        "en": "{hotel}: dropped to {currency} {amount}",
    },
    "hotels.message.price_rose_to": {
        "es": "{hotel}: subió a {currency} {amount}",
        "en": "{hotel}: rose to {currency} {amount}",
    },
    "hotels.message.percentage_drop": {
        "es": "{hotel}: bajó {pct} ({baseline} → {current} {currency})",
        "en": "{hotel}: dropped {pct} ({baseline} → {current} {currency})",
    },
    "hotels.message.percentage_increase": {
        "es": "{hotel}: subió {pct} ({baseline} → {current} {currency})",
        "en": "{hotel}: rose {pct} ({baseline} → {current} {currency})",
    },
    "hotels.message.provider_changed": {
        "es": "{hotel}: el proveedor más barato cambió de {previous_provider} a {current_provider}",
        "en": "{hotel}: cheapest provider changed from {previous_provider} to {current_provider}",
    },
    "hotels.message.availability_returned": {
        "es": "{hotel}: vuelve a estar disponible a {currency} {amount}",
        "en": "{hotel}: available again at {currency} {amount}",
    },
    # ── Security activity titles ──
    "security.title.register": {
        "es": "Cuenta creada",
        "en": "Account created",
    },
    "security.title.login": {
        "es": "Nuevo acceso a tu cuenta",
        "en": "New access to your account",
    },
    "security.title.refresh": {
        "es": "Sesión renovada",
        "en": "Session renewed",
    },
    "security.title.close_all_sessions": {
        "es": "Sesiones cerradas",
        "en": "Sessions closed",
    },
    "security.title.password_change": {
        "es": "Contraseña actualizada",
        "en": "Password updated",
    },
    "security.title.forgot_password_requested": {
        "es": "Recuperación solicitada",
        "en": "Recovery requested",
    },
    "security.title.password_reset": {
        "es": "Contraseña restablecida",
        "en": "Password reset",
    },
    "security.title.default": {
        "es": "Actividad de seguridad",
        "en": "Security activity",
    },
    "security.body.with_ip": {
        "es": "Actividad registrada desde {ip}.",
        "en": "Activity recorded from {ip}.",
    },
    "security.body.without_ip": {
        "es": "Actividad registrada en tu cuenta.",
        "en": "Activity recorded on your account.",
    },
}


def t(locale: str, key: str, **params: object) -> str:
    """Resolve a translation key for the given locale, with optional params.

    Falls back to Spanish if the locale or key is unknown.
    """
    entry = _STRINGS.get(key)
    if entry is None:
        return key

    template: str | None = entry.get(locale) or entry.get("es")
    if template is None:
        return key

    if not params:
        return template

    result = template
    for param_key, param_value in params.items():
        result = result.replace(f"{{{param_key}}}", str(param_value))
    return result
