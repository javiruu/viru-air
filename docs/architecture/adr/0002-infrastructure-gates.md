# ADR 0002: Decision Gates de Infraestructura Opcional (Valkey, Trigger.dev, Typesense, Temporal)

**Estado:** APROBADO  
**Fecha:** 2026-09-12  
**Decisores:** Equipo de arquitectura Viru / Codex  
**Documentos de referencia:**  
- `viru-modernization-codex/00_GLOBAL_GUARDRAILS.md` (Reglas 7 y 10)  
- `viru-modernization-codex/13_VALKEY.md`  
- `viru-modernization-codex/14_TRIGGER_DEV.md`  
- `viru-modernization-codex/15_TYPESENSE.md`  
- `viru-modernization-codex/16_TEMPORAL.md`  

---

## Contexto

El paquete de modernización establece que las tecnologías de infraestructura (Fase 4) **no deben instalarse por inercia o por ser modernas**, sino únicamente tras la superación de un decision gate respaldado por métricas demostrables de necesidad, volumen o coste operativo.

---

## Decisiones por Tecnología

### 1. Valkey / Redis (`13_VALKEY.md`) — ESTADO: READY / DEFERRED
- **Evaluación:** El backend ya cuenta con una capa compatible con Redis en `app/infrastructure/redis_client.py` y `services/quick_search_redis_hot_layer.py`. Cuando no hay Redis/Valkey disponible, Viru funciona de manera autónoma con singleflight en memoria y base de datos local sin degradación.
- **Decisión:** Mantener la capa como opcional y diferir el despliegue de un clúster dedicado de Valkey hasta que métricas de producción (p95 de proveedores, límites de rate limit de Ryanair/Vueling) justifiquen su coste operativo.

### 2. Trigger.dev (`14_TRIGGER_DEV.md`) — ESTADO: NOT_APPLICABLE / DEFERRED
- **Evaluación:** Trigger.dev es una plataforma orientada fundamentalmente a TypeScript/Node.js. El 100% de los background workers de Viru (`fare_memory_revalidation_worker`, `hotels_sweep`, `notifications`) están escritos en Python nativo acoplados a SQLAlchemy y scrapers.
- **Decisión:** No cruzar una frontera innecesaria de lenguajes. Los workers existentes cuentan con control de concurrencia, leases, jitter y retries que cubren el caso de uso actual.

### 3. Typesense (`15_TYPESENSE.md`) — ESTADO: NOT_APPLICABLE
- **Evaluación:** El autocompletado de búsqueda de Viru opera sobre un catálogo maestro local de aeropuertos en memoria (`app/infrastructure/airports_catalog.py`) con normalización de diacríticos y prefijos IATA que responde en <2 ms.
- **Decisión:** Descartar Typesense. Desplegar un clúster de búsqueda distribuida para un catálogo estático de ~4.000 aeropuertos representaría complejidad accidental (*AI slop*).

### 4. Temporal (`16_TEMPORAL.md`) — ESTADO: NOT_APPLICABLE
- **Evaluación:** La regla 10 de los guardrails globales prohíbe explícitamente: *"No introducir Temporal si Trigger.dev o workers actuales resuelven el problema"*. Los flujos de Viru no requieren sagas distribuidas de semanas de duración ni coordinación multi-cluster.
- **Decisión:** Descartar Temporal. La orquestación en segundo plano se mantiene gobernada por las tablas `revalidation_job` y los workers asíncronos del backend.

---

## Consecuencias

- Arquitectura limpia, contenida y portable sin sobrecoste de infraestructura.
- 100% alineada con los principios de diseño y guardrails anti-slop del proyecto.

