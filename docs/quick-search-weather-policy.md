# Quick-Search Weather Policy (Open-Meteo)

## Scope
Weather in Quick-Search is **auxiliary**. It must never block flight search results.

## Forecast horizon rule
For the current forecast endpoint (`/v1/forecast`), frontend queries weather only when:
- `start_date >= today (UTC)`
- `end_date <= today + 14 days (UTC)`

If selected dates are outside that window, weather is treated as unavailable and no provider request is sent.

## UX fallback
When weather is unavailable by range:
- show a non-alarmist message (`weatherUnavailableRange`)
- keep flight search flow unchanged

When provider fails unexpectedly:
- show generic weather warning (`weatherError`)
- keep flight search flow unchanged

## Error semantics
- Provider `400` with "out of allowed range" is classified as out-of-range (not system failure).
- Any weather failure remains best-effort and isolated from core quick-search execution.
