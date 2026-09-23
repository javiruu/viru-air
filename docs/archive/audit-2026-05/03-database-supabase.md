# 03 — Base de Datos, Supabase, RLS y Autoridad de Migraciones

**Fecha:** 2026-09-12  
**Commit auditado:** 91e6717d9bbd43d4ba148c6a114426266fabb823  

## 1. Resolucion de Autoridad Unica de Schema

El informe anterior senalaba como autoridad a `SQLAlchemy / Alembic / Supabase SQL`. Tras auditar la totalidad de las 65 migraciones de Alembic y el runtime de backend, se resuelve y dictamina la autoridad formal:

| Schema / Objetos | Model Authority | Migration Authority | Runtime Access | Notas |
|---|---|---|---|---|
| **public (todas las tablas de negocio)** | SQLAlchemy (`backend/app/infrastructure/db/models.py`) | **Alembic** (`backend/alembic/versions/`, 65 revisiones) | SQLAlchemy Session / Engine | **Autoridad Unica.** Alembic gestiona la creacion, indices, claves foraneas y alteraciones de todas las tablas de la aplicacion. |
| **flight_watch (tabla de watchlist)** | SQLAlchemy (`FlightWatch`) | **Alembic** (migracion 0006 y sucesivas) | SQLAlchemy Session | Gestionada historicamente y con constraints FK activas en Alembic. |
| **supabase/migrations/*** | N/A (Scaffold experimental) | Supabase CLI (No conectado) | Ninguno (0 call sites) | **EXPERIMENTAL_ONLY / PILOT_SCAFFOLD**. No aplica DDL sobre la base de datos de runtime. |

### Decision Arquitectonica
**Alembic es la unica autoridad legitima de migraciones de la base de datos.**
No se permite que Supabase ejecute DDL compitiendo con Alembic sobre el schema `public`. Cualquier adopcion futura de Supabase debe o bien consumir el schema gestionado por Alembic, o formalizarse mediante una migracion de autoridad explicita.

## 2. Reproducibilidad Local Supabase
- **Supabase CLI:** No instalado en el host (`not installed`).
- **Estado de reproduccion:** `BLOCKED_ENVIRONMENT`. No se ejecuto `supabase db reset` ni `supabase test db` por indisponibilidad de Supabase CLI en la maquina local.
- **Garantia de seguridad:** NO se ejecutaron comandos remotos destructivos (`--linked` / `db push`).

## 3. Analisis de Politicas RLS (`supabase/migrations/20260912000001_create_flight_watch.sql`)
La migracion piloto declara 5 politicas:
1. `Users can select own flight_watch`: `TO authenticated USING ((SELECT auth.uid())::text = user_id)` -> Correcto para aislamiento por usuario.
2. `Users can insert own flight_watch`: `TO authenticated WITH CHECK ((SELECT auth.uid())::text = user_id)` -> Correcto.
3. `Users can update own flight_watch`: `TO authenticated USING/WITH CHECK` -> Correcto.
4. `Users can delete own flight_watch`: `TO authenticated USING` -> Correcto.
5. `Service role has full access to flight_watch`: `TO service_role USING (true) WITH CHECK (true)` -> **Politica enganosa / redundante**. En PostgreSQL/Supabase el rol `service_role` tiene el atributo nativo `BYPASSRLS`. La inclusion de una politica permisiva explicita es redundante con el comportamiento de Postgres.

## 4. Estado de Adopcion de Supabase
- **Clasificacion final:** `EXPERIMENTAL_ONLY`.
- **Justificacion:** No existe ningun cliente de Supabase instanciado en el backend ni en el frontend. La persistencia real de Watchlist reside en SQLite/PostgreSQL gestionada a traves de los repositorios SQLAlchemy del backend.

## 5. Integridad de Schema y Datos
- **Alembic:** 65 versiones ordenadas cronologicamente desde `0001_initial` hasta `0062_prune_legacy_expiry_indexes`.
- **Integridad referencial:** Las tablas criticas (`flight_watch`, `alert_rules`, `alert_events`, `community_trending_snapshots`) cuentan con Foreign Keys con politicas de cascada (`ondelete="CASCADE"`) e indices operacionales dedicados.

