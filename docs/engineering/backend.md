# Backend

**Estado:** vivo  
**Última revisión:** 2026-05-11  
**Fuente de verdad:** sí  
**Área:** engineering

## Resumen

El backend de Viru Tracker está implementado con FastAPI y organiza API, dominio, infraestructura y servicios bajo `backend/app/`.

## Cuándo usar este documento

Úsalo como punto de entrada antes de abrir contratos más específicos o tests del backend.

## Contenido principal

- Stack base verificado: Python 3.12+, FastAPI, SQLAlchemy, Alembic.
- Punto de entrada: `backend/app/main.py`.
- Endpoints operativos visibles:
  - `/health`
  - `/ready`
- Dominio documentado con mayor detalle en:
  - [Quick Search contract](../reference/backend/quick-search-contract.md)
  - [Quick Search acceptance checklist](../reference/backend/quick-search-acceptance-checklist.md)

## Relacionado

- [Estado actual](../overview/current-state.md)
- [Referencia backend](../reference/README.md)
- [Runbooks](../runbooks/)
