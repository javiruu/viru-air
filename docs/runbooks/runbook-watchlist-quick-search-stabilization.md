# Runbook - estabilizacion de `/watchlist` y `/quick-search`

**Estado:** vivo  
**Ultima revision:** 2026-06-05  
**Fuente de verdad:** si  
**Area:** runbook

## Objetivo

Dejar una secuencia corta y reproducible para:

- arrancar un entorno local limpio;
- reproducir incidencias reales en `/watchlist` y `/quick-search`;
- distinguir fallo de contrato, UI, datos locales o degradacion de provider;
- validar un cierre de estabilizacion con evidencia.

## Linea base local

### Backend

```powershell
cd C:\Users\javiru\Desktop\viru-tracker\backend
python -m alembic upgrade head
python -m uvicorn app.main:app --port 8000
```

Suposiciones operativas:

- `backend/.env` existe;
- `JWT_SECRET` no usa `change-me`;
- la base SQLite local o la base configurada esta migrada.

### Frontend

```powershell
cd C:\Users\javiru\Desktop\viru-tracker\frontend
npm install
npm run dev
```

Configuracion recomendada:

- `NEXT_PUBLIC_API_URL=/api/v1`
- `NEXT_PUBLIC_LOCAL_API_ORIGIN=http://127.0.0.1:8000`

## Comprobacion de arranque limpio

1. Verifica que `http://127.0.0.1:8000` escucha en backend.
2. Verifica que `http://127.0.0.1:3000/quick-search` responde desde frontend.
3. Registra una cuenta nueva para evitar sesgo por sesion antigua o datos locales heredados.
4. Abre `/watchlist` y `/quick-search` con esa sesion recien creada.

## Que capturar siempre

Para cada incidencia:

- ruta exacta;
- interaccion exacta;
- payload real si hay submit;
- respuesta HTTP real;
- consola del navegador;
- logs backend filtrados por `correlation_id` o por ruta;
- frecuencia o si es intermitente;
- si ocurre solo con datos ya existentes o tambien con cuenta limpia.

## Matriz rapida de diagnostico

### Si falla `/watchlist`

- `GET /api/v1/watchlist` falla:
  revisar auth, `resolveApiBase`, token y backend.
- lista carga pero detalle/historico no:
  revisar `POST /api/v1/prices/history/batch` y estados vacios parciales.
- se ven claves i18n crudas:
  revisar `frontend/src/i18n/domains/watchlist.ts` y consumidores de `t(...)`.
- el mapa da warnings o estados raros:
  revisar inicializacion de `MapLibre`, estilo cargado y orden de montaje.

### Si falla `/quick-search`

- `Buscar` no se habilita:
  revisar validacion de inputs, fecha y catalogo `GET /api/v1/airports/seeds`.
- `POST /api/v1/search/quick` devuelve `200` pero sin resultados:
  distinguir entre vacio real y degradacion de provider usando `meta.warnings_structured`, `meta.provider_status` y el log `quick_search trace=...`.
- aparecen rarezas solo en local:
  revisar `.env`, base URL real del navegador y sesion.
- se ven avisos de pool o rafagas:
  revisar `concurrency_limit`, `provider_calls`, `provider_statuses` y pool HTTP de providers.

## Senales canonicas de degradacion

`/quick-search` puede estar tecnicamente sano y aun asi mostrar estado degradado si el provider real falla.

Comprobar:

- `meta.provider_status.overall_status`
- `meta.provider_status.providers[]`
- `meta.warnings_structured`
- la UI debe fusionar `filters.warnings` y `meta.warnings_structured` para no perder warnings canonicos cuando cambie el provider o la capa de agregacion
- log backend:

```text
quick_search trace=... results=... planned_pairs=... requested_units=... rescue=... winning_step=... warnings=... provider_statuses=... concurrency_limit=...
```

Interpretacion:

- `results=0` + `warnings` de provider:
  degradacion o vacio real, no necesariamente bug de UI.
- `provider_total_outage`:
  fallo externo o indisponibilidad total de providers.
- `provider_error_partial` o `provider_timeout_partial`:
  respuesta parcial servida con rescate o con filtros relajados.

## Checklist de cierre

### `/watchlist`

1. Carga con cuenta limpia.
2. Permite crear una ruta.
3. Renderiza estado vacio sin claves i18n crudas.
4. Permite refresco simple y masivo sin romper resumen.
5. No emite warnings funcionales del mapa por estilo no cargado.

### `/quick-search`

1. Carga con cuenta limpia.
2. Permite completar origen, destino y fecha.
3. Lanza `POST /api/v1/search/quick`.
4. Distingue entre resultado vacio, error y degradacion parcial.
5. Los logs dejan rastro suficiente para explicar el resultado.

## Comandos de regresion minimos

### Frontend

```powershell
cd C:\Users\javiru\Desktop\viru-tracker\frontend
npm test -- --test-name-pattern="quick-search-screen-state|quick-search-refactor-utils|watchlist runtime guards"
npm run lint
```

### Backend

```powershell
cd C:\Users\javiru\Desktop\viru-tracker
python -m pytest backend\tests\unit\test_provider_session_pooling.py backend\tests\integration\test_watchlist_flow.py backend\tests\integration\test_watchlist_refresh_cooldown.py backend\tests\integration\test_quick_search_returns_results.py backend\tests\integration\test_quick_search_realistic_happy_path.py
```

## Riesgos residuales actuales

- `quick-search` sigue dependiendo de disponibilidad real de provider.
- En entorno headless pueden aparecer warnings WebGL del navegador; no confundirlos con regresion funcional del mapa.
- Hay un warning de lint preexistente en `frontend/src/modules/hotels/components/HotelSearchPanel.tsx` no relacionado con esta campana.
