# Database Runtime Authority & Configuration Proof

**Date:** 2026-09-12  
**Authority:** 02_SUPABASE_REMOTE_DATABASE_CUTOVER.md  
**Target Architecture:** Hosted Supabase PostgreSQL as the ONLY runtime database

---

## 1. Runtime Database Configuration Audit

### Effective Connection String Resolution
- **Environment Variable:** DB_URL (defined in ackend/app/infrastructure/db/session.py)
- **Dialect Supported:** postgresql+psycopg:// (using psycopg[binary]>=3.2.0) or postgresql://
- **Fallback Policy (Development/Default):** If DB_URL is unset, defaults to local SQLite (sqlite:///viru.db).
- **Production / Staging Enforcement:** DB_URL must point to remote Supabase with sslmode=require.
- **Driver:** psycopg3 (binary asynchronous/synchronous driver).

### Connection Pooling & Engine Configuration
Defined in ackend/app/infrastructure/db/session.py:
- uture=True (SQLAlchemy 2.0 native style)
- pool_pre_ping=True (health verification before borrowing connection from pool)
- When dialect is PostgreSQL (Supabase):
  - pool_size: Configured via DB_POOL_SIZE (default: 10)
  - max_overflow: Configured via DB_MAX_OVERFLOW (default: 20)
  - pool_timeout: Configured via DB_POOL_TIMEOUT_SECONDS (default: 30)
  - pool_recycle: Configured via DB_POOL_RECYCLE_SECONDS (default: 1800)

### Background Workers Configuration
- **Revalidation Worker (pp/services/revalidation_worker_entrypoint.py):** Shares SessionLocal from pp.infrastructure.db.session. Uses identical DB_URL.
- **Notification Worker (pp/worker/notifications.py):** Defaults to session_factory = SessionLocal. Uses identical DB_URL.
- **Hotel Sweep Worker (pp/worker/hotels_sweep.py):** Uses session_factory = SessionLocal. Uses identical DB_URL.

### Test Suite Configuration
- Unit tests use mock sessions or isolated test databases (sqlite:///:memory: or temporary SQLite fixture) configured in ackend/tests/conftest.py.
- Integration tests accept remote TEST_SUPABASE_DB_URL or DB_URL.
- No local database containers or containerized PostgreSQL services are used.

### Fallback Paths Inventory
1. ackend/app/infrastructure/db/session.py: lines 7-13: fallback to local iru.db if DB_URL is empty.
2. ackend/alembic.ini: default sqlalchemy.url = sqlite:///./viru.db (Alembic retired as DDL authority).
3. iniciar_viru.ps1: sets DB_URL if not already set.

---

## 2. Remote Supabase Target Specification

- **Host Category:** Remote Hosted Supabase PostgreSQL.
- **Port:** 5432 (Direct / Session Mode via Supavisor).
- **SSL Requirement:** sslmode=require enforced on all connection strings.
- **Connection Mode:** Session Mode / Direct connection to preserve SQLAlchemy prepared statements and ORM transaction boundaries.
