# Root Git Reconciliation Report

Fecha: 2026-05-11  
Workspace: `C:\Users\javiru\Desktop\viru-tracker`

## Resumen ejecutivo

La raíz ya tiene `.git`, rama `main` y `origin` correcto (`https://github.com/javiruu/viru-tracker.git`), pero **todavía no está lista para publicar como único repo sin una reconciliación adicional**.

Bloqueos detectados (estado previo):
- No existe commit local en la raíz (`HEAD` inexistente).
- Todo el árbol aparece como `untracked` respecto al índice local actual.

Con ese estado previo, no era seguro hacer commit/push de reconciliación.

Actualización posterior (2026-05-11):
- Se ejecutó `git fetch origin main` + `git reset --mixed origin/main` para crear base local sin sobrescritura destructiva.
- `users_prueba.txt` se trata como archivo intencional del proyecto por decisión explícita del usuario.

## Estado Git inicial

Comandos:
- `git status --short --ignored`
- `git branch --show-current`
- `git remote -v`
- `git rev-parse HEAD`
- `git rev-parse origin/main`
- `git log --oneline -5`

Resultado:
- Rama actual: `main`
- Remote: `origin` fetch/push a `https://github.com/javiruu/viru-tracker.git`
- `origin/main`: `bac86841d405ffc0dc36d5cef80037aecf91dc56`
- `HEAD`: inexistente (fatal: unknown revision)
- `HEAD == origin/main`: no verificable (no hay `HEAD`)
- Staged: ninguno
- Unstaged: ninguno (no hay archivos trackeados locales)
- Untracked: masivo (prácticamente todo el repo)
- Ignored: presentes (caches, venv, db local, `_publish_repo`, etc.)

## Clasificación de diferencias

Fuentes usadas:
- `git status --short`
- `git status --short --ignored`
- `git diff --name-only`
- `git diff --cached --name-only`
- `git ls-files --others --exclude-standard`
- `git ls-files --ignored --others --exclude-standard`

Clasificación por categoría:

- `versionar ahora` (intencionales de migración):
  - `.gitignore`
  - `users_prueba.example.txt`
  - `scripts/tree-clean.ps1`
  - `README.md`
  - `docs/reference/done-checklist.md`
  - `scripts/install-git-hooks.ps1`
  - `scripts/release_guard.ps1`
  - `docs/reports/remove-publish-repo-migration-audit.md`
  - `docs/reports/remove-publish-repo-migration-final.md`
  - `docs/reports/docs-sanitize-audit.md` (nota posterior)
  - `docs/reports/docs-sanitize-final-report.md` (nota posterior)
  - `docs/reports/docs-sanitize-qc-report.md` (nota posterior)
  - `docs/reports/root-git-reconciliation-report.md`

- `ignorar/local`:
  - `_publish_repo/`
  - `users_prueba.txt`
  - `tree_filtrado.txt` (raíz)
  - `.env`, `backend/.env`, `bot_ryanair_referencia_no_tocar/.env`
  - `token.txt`, `bot_ryanair_referencia_no_tocar/token.txt`
  - `viru.db`, `backend/viru.db`
  - `%TEMP%/`, `.venv/`, `venv/`, `.next/`, `node_modules/`, `logs/`, `tmp/`, `test-results/`, `__pycache__/`, `_bench_before/`, `_bench_after/`

- `generado/cache`:
  - rutas bajo `%TEMP%/npm-cache`
  - rutas bajo `backend/.venv/`
  - `frontend/.next/`, `frontend/node_modules/`
  - `__pycache__`, `test-results`, logs

- `riesgo sensible`:
  - no bloqueante en esta pasada respecto a `users_prueba.txt` (archivo intencional confirmado por el usuario)

- `conflicto o divergencia`:
  - divergencia estructural alta: índice local sin `HEAD` + árbol completo untracked, imposibilita reconciliación limpia en un solo commit sin estrategia controlada.

## Verificación de archivos de migración

Revisión por ruta/nombre y referencias (`rg "_publish_repo"` en archivos objetivo):
- Cambios de migración detectados como intencionales en los archivos listados arriba.
- No se tocó `AGENTS.md`.
- Las menciones en reportes históricos se mantienen con nota posterior (no reescritura histórica completa).

## Seguridad de archivos sensibles/locales

Comandos:
- `git check-ignore -v _publish_repo users_prueba.txt tree_filtrado.txt viru.db token.txt .env backend/.env bot_ryanair_referencia_no_tocar/.env bot_ryanair_referencia_no_tocar/token.txt`
- `git ls-files -- users_prueba.txt tree_filtrado.txt viru.db token.txt .env backend/.env bot_ryanair_referencia_no_tocar/.env bot_ryanair_referencia_no_tocar/token.txt`
- `git ls-tree -r origin/main -- users_prueba.txt tree_filtrado.txt viru.db token.txt .env backend/.env bot_ryanair_referencia_no_tocar/.env bot_ryanair_referencia_no_tocar/token.txt`

Resultado:
- Ignorados localmente por `.gitignore`: sí (`_publish_repo`, `users_prueba.txt`, `tree_filtrado.txt`, `viru.db`, `token.txt`, `.env` y variantes verificadas).
- Trackeados localmente: no (`git ls-files` vacío para esa lista).
- Presencia en `origin/main`:
  - `users_prueba.txt`: sí (intencional, se conserva).
  - resto de sensibles consultados: no detectados en esa comprobación puntual.

## Prueba de `scripts/tree-clean.ps1`

Comandos ejecutados:
- `powershell -ExecutionPolicy Bypass -File .\scripts\tree-clean.ps1 -Mode repo`
- `powershell -ExecutionPolicy Bypass -File .\scripts\tree-clean.ps1 -Mode docs`
- `powershell -ExecutionPolicy Bypass -File .\scripts\tree-clean.ps1 -Mode live-docs`

Resultado:
- El script funciona en los 3 modos.
- `docs` y `live-docs` excluyen `_publish_repo`, `node_modules`, `.venv`, `venv`, `.next`, `.next_broken_*`, `npm-cache`, `.pytest_cache`, `__pycache__`, `logs`, `test-results`, `tmp`, `%TEMP%`, `_bench_before`, `_bench_after`.
- En `Mode repo` se observan aún `backend/.env`, `bot_ryanair_referencia_no_tocar/.env`, `token.txt`, `viru.db` porque el filtro actual del script excluye directorios y patrones de carpetas, pero no oculta todos esos ficheros por nombre en salida de árbol.

## Qué debe versionarse ahora

Si se resuelve primero la divergencia de base, versionar este paquete mínimo de migración:
- `.gitignore`
- `users_prueba.example.txt`
- `scripts/tree-clean.ps1`
- `README.md`
- `docs/reference/done-checklist.md`
- `scripts/install-git-hooks.ps1`
- `scripts/release_guard.ps1`
- `docs/reports/remove-publish-repo-migration-audit.md`
- `docs/reports/remove-publish-repo-migration-final.md`
- `docs/reports/docs-sanitize-audit.md`
- `docs/reports/docs-sanitize-final-report.md`
- `docs/reports/docs-sanitize-qc-report.md`
- `docs/reports/root-git-reconciliation-report.md`

## Qué NO debe versionarse

- `_publish_repo/`
- `users_prueba.txt`
- `tree_filtrado.txt` (raíz)
- `.env`, `.env.*`, `token.txt`, `viru.db`
- caches, builds y temporales (`node_modules`, `.venv`, `.next`, logs, tmp, test-results, `%TEMP%`, etc.)

## Riesgos y veredicto

Riesgos:
1. `users_prueba.txt` está en `origin/main` (sensible).
2. La raíz no tiene `HEAD` local; no hay base de commit local para reconciliación segura.
3. El árbol completo figura untracked, por lo que un commit directo podría mezclar demasiados cambios sin trazabilidad fina.

Veredicto:
- `_publish_repo` puede mantenerse como referencia temporal, pero no hace falta para flujo operativo diario.
- **No borrar `_publish_repo` todavía** hasta cerrar esta reconciliación y publicar desde raíz con base limpia.
- **La raíz aún no está lista** para ser el único repo publicado en esta pasada.
- Falta: estrategia controlada para alinear base local con `origin/main` sin reset destructivo y con tratamiento explícito del `users_prueba.txt` histórico.

## Commit/push en esta pasada

No se realizó commit ni push (intencional).  
Motivo: divergencia no resuelta + riesgo sensible detectado.
