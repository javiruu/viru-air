# Runbook — Activación del runtime hotelero (imagen GHCR, Secret, migración, CronJob)

**Estado:** vivo  **Última revisión:** 2026-08-06  **Fuente de verdad:** sí  **Área:** runbooks

> Este runbook publica y activa el runtime hotelero preparado en la Fase H09/H45/H55/H56:
> imagen multi-stage `backend/Dockerfile`, Job de migración separado y CronJob de sweep `--once`
> suspendidos por defecto. La activación aquí documentada es **solo Mock y staging**:
> no autoriza provider comercial ni tráfico live (gates H07/H37/H43).

## Precondiciones (gates)

Antes de empezar:

- [ ] gates H43 (flags/kill switch), H45 (release/smoke) y H55 (continuidad) revisados y firmados por owner;
- [ ] `scripts/release_guard.ps1` limpio (rama `main`, sin artefactos ni secretos en el alcance);
- [ ] provider = **mock** únicamente; sin `MAKCORPS_API_KEY` ni credencial comercial;
- [ ] DB objetivo aislada/staging, con backup/restore verificado o procedimiento H11/H55;
- [ ] acceso a un cluster Kubernetes (kubectl) con permisos para Secrets, Jobs y CronJobs.

## 1. Publicar la imagen a GHCR

1. Ejecutar el workflow **Release** (`infra/github/workflows/release.yml`) desde GitHub Actions:
   - `quality-gates` corre tests backend, build frontend y build de imagen (sin push);
   - `publish-image` hace login con `GITHUB_TOKEN` (`packages: write`) y publica
     `ghcr.io/<owner>/<repo>/backend:sha-<commit>` (inmutable) y `:latest`.
2. La primera publicación crea el paquete bajo el repositorio; confirmar que aparece en
   `https://github.com/<owner>/<repo>/pkgs/container/<repo>%2Fbackend`.
3. Registrar el digest inmutable del build:
   ```bash
   docker buildx imagetools inspect ghcr.io/<owner>/<repo>/backend:sha-<commit>
   ```

Límite: no declarar la imagen "aprobada" hasta ver el digest y un `docker run` de smoke
(build exit 0, `/health` 200) contra la imagen publicada.

## 2. Crear el Secret `viru-backend-runtime`

El Secret debe contener las keys que consumen la API, el CronJob y el Job de migración:

| Key | Uso |
|---|---|
| `DB_URL` | conexión a la DB (requerida por el Job de migración, el CronJob y la API) |
| `JWT_SECRET` | requerida por `backend/app/core/security.py` al importar; min 32 bytes aleatorios |
| `TOKEN_HASH_SECRET` | opcional; si falta, usa `JWT_SECRET` |

Preferido (sin escribir el valor en disco):

```bash
kubectl create secret generic viru-backend-runtime \
  --from-literal=DB_URL='postgresql://user:pass@host:5432/viru' \
  --from-literal=JWT_SECRET='<openssl rand -hex 32>' \
  --dry-run=client -o yaml | kubectl apply -f -
```

Si se usa manifest: copiar `infra/k8s/runtime-secret.example.yaml`, rellenar `stringData`,
aplicar y borrar el archivo. **Nunca** commitear valores reales.

## 3. Ejecutar y verificar la migración

El Job de migración existe suspendido en `infra/k8s/hotels-migrate-job.yaml`.

1. Aplicar el Job (sigue suspendido, no crea pods todavía):
   ```bash
   kubectl apply -f infra/k8s/hotels-migrate-job.yaml
   ```
2. Reanudarlo y esperar:
   ```bash
   kubectl patch job viru-hotels-migrate -p '{"spec":{"suspend":false}}'
   kubectl wait --for=condition=complete job/viru-hotels-migrate --timeout=300s
   ```
3. Verificar la revisión de schema alcanzada:
   ```bash
   kubectl logs job/viru-hotels-migrate --tail=5
   # esperado: "Running upgrade ... -> 0041_add_community_trending_snapshots"
   ```

Límite: el Job debe ejecutarse contra la DB/Secret real; la evidencia local (SQLite aislada)
no sustituye esta verificación. No ejecutar `contract` ni borrar columnas como parte del paso.

## 4. Activar el CronJob de sweep (Mock) vía overlay

El overlay `infra/k8s/overlays/staging/kustomization.yaml` es el **único** lugar que
des-suspende el CronJob y enciende las flags Mock (`HOTEL_FEATURE_ENABLED=true`,
`HOTEL_SWEEP_ENABLED=true`, `HOTEL_PROVIDER=mock`).

1. Ajustar la imagen publicada en `images:` del overlay (preferir `sha-<commit>`; si el workflow se ejecutó con una `IMAGE_NAME` distinta a `backend`, usar el nombre real publicado):
   ```yaml
   images:
     - name: ghcr.io/your-org/viru-backend
       newName: ghcr.io/<owner>/<repo>/backend
       newTag: sha-<commit>
   ```
2. Validar el render sin tocar el cluster:
   ```bash
   kubectl kustomize infra/k8s/overlays/staging > /tmp/rendered.yaml
   grep -E 'suspend|HOTEL_PROVIDER|image:' /tmp/rendered.yaml
   kubectl apply --dry-run=server -k infra/k8s/overlays/staging
   ```
   Esperado: el CronJob queda `suspend: false`, el Job de migración sigue `suspend: true`.
3. Aplicar:
   ```bash
   kubectl apply -k infra/k8s/overlays/staging
   ```

## 5. Verificación de un sweep real

El CronJob programa `0 * * * *` con `concurrencyPolicy: Forbid`. Para validar sin esperar:

```bash
kubectl create job --from=cronjob/viru-hotels-sweep viru-hotels-sweep-manual-01
kubectl wait --for=condition=complete job/viru-hotels-sweep-manual-01 --timeout=300s
kubectl logs job/viru-hotels-sweep-manual-01 -l app=viru-hotels-sweep --tail=10
```

Esperado en logs (evento estructurado):

```json
{"event": "hotel_sweep_cycle", "mode": "once", "provider": "mock",
 "provider_run_id": "...", "status": "completed", "items_processed": 3}
```

En DB (consulta aislada):

```sql
SELECT provider, status, items_processed, started_at, finished_at
FROM hotel_provider_run ORDER BY started_at DESC LIMIT 5;
```

Chequeo de seguridad tras el run:

- `HOTEL_SWEEP_ENABLED=false` + `kubectl create job --from=cronjob/viru-hotels-sweep x` → el worker
  debe emitir `hotel_sweep_disabled` y no crear `HotelProviderRun` nuevo (kill switch verificado);
- cero llamadas externas: con provider mock y `HOTEL_GEOCODER_ENABLED=false` no debe haber red;
- `HotelProviderRun` lleva `provider_run_id` y snapshots vinculados (contrato H56).

## 6. Rollback

Detener el scheduling sin borrar datos:

```bash
kubectl patch cronjob viru-hotels-sweep -p '{"spec":{"suspend":true}}'
kubectl delete job viru-hotels-sweep-manual-01 --ignore-not-found
```

Para volver a una imagen anterior: cambiar `newTag` del overlay a otro `sha-<commit>` y
re-aplicar. No borrar snapshots, tracked offers ni alert events en el rollback (H45/H55).

## 7. Registro de evidencia

Guardar en el paquete H45/H56:

```text
image_digest / tag publicado
secret_created_at (sin valores)
migration_revision alcanzada
cronjob_last_schedule_time / runs completed
provider_run_id del smoke
kill_switch_result
owner / approver / fecha
```

**Regla:** el CronJob vuelve a `suspend: true` en el base y en el overlay de producción
hasta que provider, presupuesto (H37), observabilidad (H41) y gates H43/H45/H55 estén
aprobados con evidencia reproducible.
