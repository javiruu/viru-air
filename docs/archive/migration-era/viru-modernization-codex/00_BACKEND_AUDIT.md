# Auditoría obligatoria del backend y frontend actuales

Esta etapa no instala nada. Su propósito es impedir una migración basada en suposiciones.

## Entregables

Codex debe crear `docs/architecture/current.md` con:

1. Diagrama textual de requests desde UI → API → servicios → proveedores → persistencia.
2. Tabla de endpoints con método, ruta, handler, auth, input, output y consumidores.
3. Inventario de persistencia: tablas, JSON, SQLite/Postgres, ficheros, caches, stores in-memory.
4. Inventario de auth/sesiones/JWT/OAuth y dónde se verifican permisos.
5. Inventario de jobs/cron/workers y sus mecanismos de retry, deduplicación, locks y observabilidad.
6. Inventario de providers/scrapers y normalización de datos.
7. Inventario de duplicaciones y código muerto con evidencia de referencias.
8. Riesgos de seguridad: secretos, autorización en frontend, SQL dinámico, endpoints inseguros, CORS, SSRF, uploads, RLS inexistente, etc.
9. Matriz KEEP / REFACTOR / REPLACE / DELETE / UNKNOWN.
10. Métricas de tamaño: LOC aproximadas por dominio y archivos con complejidad anormal.

## Búsquedas anti-slop

Buscar y clasificar, sin borrar automáticamente:

- `Service`, `Manager`, `Repository`, `Adapter`, `Facade`, `Helper`, `Util` redundantes;
- wrappers de un solo uso;
- modelos duplicados frontend/backend;
- `fetch` dispersos;
- `useEffect` usados para sincronizar server state;
- caches caseras;
- WebSocket managers custom;
- auth/JWT casero;
- SQL repetido;
- configuraciones duplicadas;
- TODO/FIXME/HACK;
- `any`, `@ts-ignore`, catches silenciosos;
- feature flags muertas;
- endpoints no consumidos;
- código “legacy”, “v2”, “new”, “final”, “fixed” coexistiendo.

## Baseline funcional

Documentar al menos los journeys críticos reales de Viru. No inventarlos. A partir del código/UI y, si existe, documentación del proyecto, identificar los flujos que generan valor (búsqueda, resultados, watchlist, refresco, alertas, historial, etc.) y usarlos en Playwright.

## Resultado esperado

No tocar arquitectura todavía. El output debe permitir responder sin buscar durante minutos:

- ¿Dónde se guarda X?
- ¿Quién autoriza X?
- ¿Qué endpoint lo modifica?
- ¿Qué worker lo refresca?
- ¿Qué fuente es la autoridad?
- ¿Qué parte puede reemplazarse por Supabase sin tocar el motor de búsqueda?
