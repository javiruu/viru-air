# ADR 0001: Evaluacion y Decision sobre Drizzle ORM

**Estado:** RECHAZADO (NOT_APPLICABLE)
**Fecha:** 2026-09-12
**Decisores:** Equipo de arquitectura Viru / Codex
**Documento de referencia:** viru-modernization-codex/09_DRIZZLE_DECISION.md

---

## Contexto

Viru Tracker cuenta con un backend maduro en Python con FastAPI y SQLAlchemy 2.0 como capa de persistencia y ORM, junto con Alembic para el control de versiones y migraciones de esquema (62 tablas modeladas e indexadas).

El frontend de la aplicación es Next.js 15 (React 19 / TypeScript), el cual no ejecuta consultas SQL directas contra la base de datos, sino que interactúa con el backend a través de endpoints REST tipados generados por Orval sobre el contrato OpenAPI.

Se evaluó la introducción de Drizzle ORM en el frontend o como capa intermedia de persistencia según las pautas de modernización.

---

## Evaluación contra el Decision Gate

Para incorporar Drizzle, 09_DRIZZLE_DECISION.md exige el cumplimiento simultáneo de cuatro criterios:

| Criterio | Evaluación | Estado |
|---|---|---|
| **1. Runtime TypeScript server-side con acceso SQL directo** | Next.js funciona como capa de presentación y consumo de API cliente; no realiza consultas SQL directas contra PostgreSQL. | **NO CUMPLE** |
| **2. No crear una segunda capa equivalente a ORM existente** | El backend ya cuenta con SQLAlchemy 2.0 completamente tipado y probado con 1.114 tests unitarios. Introducir Drizzle duplicaría modelos y lógica de acceso a datos. | **NO CUMPLE** |
| **3. Definir claramente quién gestiona las migraciones** | Mantener dos historiales de migración paralelos (Alembic en Python vs Drizzle Kit en TS) generaría drift y colisiones en producción. | **NO CUMPLE** |
| **4. Beneficio demostrable en un slice concreto** | No reduce código ni aporta rendimiento adicional respecto al cliente tipado generado por Orval + OpenAPI. | **NO CUMPLE** |

---

## Decisión

**Se descarta la adopción de Drizzle ORM en el proyecto actual.**

1. **Autoridad de esquema:** SQLAlchemy / Alembic / Supabase SQL Migrations permanecen como la única fuente de verdad para la estructura de la base de datos PostgreSQL.
2. **Acceso a datos del frontend:** El frontend continuará comunicándose a través de la API REST tipada generada automáticamente por Orval a partir de OpenAPI, asegurando validación en los límites y separación limpia de responsabilidades.
3. **Evitar anti-patrones:** Se prohíbe explícitamente ejecutar Drizzle en el navegador o reescribir servicios funcionales del backend Python únicamente para adoptar un ORM en TypeScript.

---

## Consecuencias

- **Positivas:** Cero deuda arquitectónica por capas redundantes. Sin duplicación de esquemas ni librerías compitiendo por la misma base de datos. Menor huella de dependencias en frontend.
- **Negativas:** Ninguna.

