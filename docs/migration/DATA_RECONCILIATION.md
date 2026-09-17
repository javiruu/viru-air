# Data Reconciliation & Preflight Audit Report

**Date:** 2026-09-12  
**Authority:** Phase 2 — `02_SUPABASE_DATABASE_CUTOVER.md`  
**Source Database:** `viru.db` (SQLite)  
**Target Architecture:** Supabase-managed PostgreSQL

---

## 1. Source Database Scan Summary

- **Total Schema Tables Defined in Codebase:** 62 tables (in `Base.metadata`)
- **Tables Existing in SQLite Database:** 47 tables
- **Tables with Populated Data:** 5 tables
- **Empty Tables:** 57 tables

---

## 2. Table Row Count & Integrity Audit

| Table Name | Source Row Count | PK Uniqueness Count | Null Violation Count | FK Orphan Count | Reconciliation Status |
|---|---|---|---|---|---|
| `airport` | 222 | 222 (100% unique) | 0 | 0 | **VERIFIED** |
| `users` | 1 | 1 (100% unique) | 0 | 0 | **VERIFIED** |
| `security_activity` | 1 | 1 (100% unique) | 0 | 0 (references valid user) | **VERIFIED** |
| `quick_search_popularity_counter` | 3 | 3 (100% unique) | 0 | 0 | **VERIFIED** |
| `quick_search_popularity_daily` | 3 | 3 (100% unique) | 0 | 0 | **VERIFIED** |
| *All other 57 tables* | 0 | 0 | 0 | 0 | **EMPTY / CLEAN** |

---

## 3. Migration Plan & Sequence

When importing into Supabase PostgreSQL:
1. Load independent dimension/seed tables first:
   - `airport` (222 rows seeded)
2. Load core user identities:
   - `users` (1 user record)
3. Load user-dependent records:
   - `security_activity` (1 row)
4. Load analytics & metrics:
   - `quick_search_popularity_counter` (3 rows)
   - `quick_search_popularity_daily` (3 rows)
5. Execute identity/sequence update for PostgreSQL autoincrement primary keys.

