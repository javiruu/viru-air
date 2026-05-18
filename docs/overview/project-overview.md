# Overview del Proyecto

**Estado:** vivo  
**Última revisión:** 2026-05-18  
**Fuente de verdad:** sí  
**Área:** overview

## Resumen

Viru Tracker es una plataforma para seguimiento de vuelos centrada en watchlists, histórico de precios, alertas y quick search. El producto prioriza claridad y soporte a la decisión con una interfaz cálida, intuitiva y con personalidad, lejos del dashboard SaaS genérico.

## Cuándo usar este documento

Usa este documento cuando necesites entender qué es Viru antes de entrar en specs, contratos o runbooks.

## Contenido principal

- Producto principal: seguimiento y comparación de rutas con foco en quick search y watchlists.
- Stack visible hoy:
  - backend con FastAPI, SQLAlchemy y Alembic;
  - frontend con Next.js, React y TypeScript;
  - datos con PostgreSQL como objetivo y SQLite para arranque local rápido.
- La documentación viva se reparte entre:
  - `docs/overview/`
  - `docs/reference/`
  - `docs/specs/`
  - `docs/ui/`
  - `docs/runbooks/`
  - `docs/qa/`

## Relacionado

- [Estado actual](current-state.md)
- [Resumen de arquitectura](architecture-summary.md)
- [Mapa del repo](repo-map.md)
- [README raíz](../../README.md)
