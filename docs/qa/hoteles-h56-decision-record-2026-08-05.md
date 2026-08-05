# H56 — DecisionRecord inicial: baseline local seguro

**Estado:** `evidence_incomplete`  
**Fecha:** 2026-08-05  
**Paquete de evidencia:** [H56-2026-08-05-local-baseline](hoteles-h56-annual-review-2026-08-05.md)  
**Contrato:** [H56](../reference/backend/hoteles-revision-anual-roadmap-h56.md)  

> Este registro no aprueba un provider, un mercado, un presupuesto ni tracking automático. Documenta qué se puede afirmar después de una ejecución local aislada y qué sigue bloqueado.

---

## Registro

```text
decision_id: H56-DR-2026-08-05-local-baseline
review_id: H56-2026-08-05-local-baseline
scope: product_and_operation
subject: first_safe_local_evidence_pack
state: evidence_incomplete
evidence_refs:
  - docs/qa/hoteles-h56-annual-review-2026-08-05.md
  - backend/tests/integration/test_hotels_api_flow.py
  - backend/tests/unit/test_hotels_sweep.py
  - backend/tests/unit/test_hotels_sweep_worker.py
  - backend/tests/unit/test_hotels_makcorps_provider.py
  - backend/app/infrastructure/db/alembic_audit.py
observed_period: 2026-08-05 local execution window
observed_local_evidence:
  - isolated SQLite upgraded to 0041_add_community_trending_snapshots
  - 2 Mock provider runs completed with 3 items each
  - 3 hotels, 3 aliases and 6 total ingestion snapshots persisted, 3 per provider run
  - replaying the same provider_run_id is idempotent and adds 0 snapshots
  - 1 price_below event linked to the second run with synthetic threshold; trigger_value=210.0
  - after the traceability fix, 3 ingestion snapshots carry the isolated sweep provider_run_id; direct ingestion without a run intentionally remains unassociated
  - real `python -m app.worker.hotels_sweep --once --provider mock` exited 0 and logged `hotel_sweep_cycle` completed with 3 items
  - two fresh worker processes simulated restart between cycles: both exited 0, persisted 2 completed runs and 6 snapshots, 3 per run
  - `infra/k8s/worker.yaml` remains a legacy placeholder command and is not evidence of Kubernetes hotel scheduling
  - `backend/Dockerfile` is now a multi-stage Python 3.12/uv.lock image contract, and CI builds it without push; immutable image digest remains unverified
  - `infra/k8s/hotels-sweep-cronjob.yaml` defines a `--once` CronJob with `concurrencyPolicy: Forbid`, `DB_URL` from a Secret and `suspend: true`
  - `infra/k8s/hotels-migrate-job.yaml` defines a separate `alembic upgrade head` Job with `DB_URL` from a Secret and `suspend: true`
  - `backend/Dockerfile` image was built and runtime-verified locally: build exit 0, `import app.main` OK, uvicorn `/health` returned 200 on a migrated isolated DB
  - plain `alembic upgrade head` executed inside the image container completed exit 0 up to `0041_add_community_trending_snapshots` on isolated SQLite
  - `python -m app.worker.hotels_sweep --once --provider mock` inside the image container logged `hotel_sweep_cycle` completed with 3 items
  - runtime gate fixes required by the image validation: `prepend_sys_path = .` in `backend/alembic.ini`; `httpx` moved from dev extras to core dependencies (app.main imports it at runtime); `JWT_SECRET` added to the CronJob and migration Job env from the runtime Secret
  - image publication/digest, Secret/DB creation, real DB migration compatibility, provider approval and active scheduling remain unverified
k8s_worker_gate: blocked_legacy_deployment_and_suspended_cronjob
k8s_migration_job_gate: blocked_suspended_unverified
known_unknowns:
  - provider live health, coverage, cost, quota and latency
  - production funnel, retention and feedback denominators
  - production flag parity across API, worker and direct job
  - production-scale traceability and sustained scheduling; the isolated Mock sweep and real `--once` worker carry provider_run_id correctly, but the legacy Kubernetes Deployment remains placeholder and the new CronJob is suspended pending operational gates
  - backup/restore, RPO/RTO and recovery drill
  - hotel delivery outside the persisted event/inbox path
  - commercial provider canary and traffic split
risk_summary: local evidence is positive for Mock/test behavior, isolated migration and sweep traceability, but insufficient for production readiness
owner: TBD
approver: TBD
effective_at: TBD
expires_at: TBD
rollback_or_exit_path: keep hotel provider and sweep in safe local/fixture mode; do not activate commercial traffic
follow_up_ticket: TBD — publish an immutable approved image, provision/validate the DB Secret and migration path, decide legacy Deployment retirement, then enable the suspended CronJob only after H43/H45/H55 gates and retain redacted run artifacts
next_review_at: TBD
```

## Observaciones que sí quedan registradas

- La suite seleccionada terminó con `81 passed in 65.76s` bajo `-m 'not network'`.
- El grafo Alembic inspeccionado tuvo `chain_ok=true`, sin `missing_down_revisions`, duplicados ni ficheros sin identificadores.
- El entrypoint `app.worker.hotels_sweep` observó `HOTEL_SWEEP_ENABLED=false` y no inició el sweep.
- El adapter Makcorps fue probado solo con sesiones/respuestas mockeadas.
- La DB SQLite en memoria del audit no tenía `alembic_version`; no se ejecutó upgrade ni restore en ese comando.
- En una ejecución posterior y separada, una SQLite temporal sí completó `upgrade head` hasta `0041_add_community_trending_snapshots`.
- En la repetición final de esa DB se observaron 2 runs Mock `completed` con 3 items cada uno, 3 hoteles, 3 aliases y 6 snapshots totales, 3 por run; un replay del mismo `provider_run_id` no duplicó snapshots.
- El segundo run produjo 1 evento local `price_below` asociado a su `provider_run_id`, con umbral sintético y `trigger_value=210.0`; no es evidencia productiva.

## Decisiones que NO se toman

```text
provider_approval: none
market_approval: none
cost_approval: none
tracking_daily_approval: none
commercial_canary_approval: none
next_roadmap_approval: none
```

## Próximo estado válido

Este registro solo puede pasar a uno de estos estados después de ampliar evidencia y obtener revisión humana:

- `remediate_throttle`: si se mantiene una capacidad limitada con gaps explícitos;
- `pause_contain`: si una superficie requiere detenerse;
- `reject_keep_fixture`: si solo debe permanecer Mock/fixture;
- `renew_promote`: únicamente para el alcance medido y aprobado, nunca por extrapolación.

La decisión sobre Makcorps, mercados, flags o implementación productiva debe tener su propio `DecisionRecord` con scope específico; este registro no los sustituye.
