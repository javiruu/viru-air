# Remove `_publish_repo` Migration Final

Fecha: 2026-05-11

## Resumen

Se preparó la raíz `C:\Users\javiru\Desktop\viru-tracker` para que sea la única fuente operativa y Git canónica local, dejando `_publish_repo` como artefacto obsoleto e ignorado.  
No se borró `_publish_repo` en esta pasada.

## Qué se hizo con la raíz Git

- Se confirmó que la raíz no tenía `.git` al inicio.
- Se inicializó Git en raíz (`git init`).
- Se configuró `origin` a `https://github.com/javiruu/viru-tracker.git`.
- Se trajo referencia de `main` usando `_publish_repo` solo para migración/verificación local:
  - `git fetch C:\Users\javiru\Desktop\viru-tracker\_publish_repo main`
- Se fijó rama local actual a `main`.
- Se detectaron diferencias masivas entre árbol local y `main` de referencia; por seguridad no se ejecutó `checkout/reset` destructivo.

## Qué se hizo con `_publish_repo`

- Se inspeccionó su estado y remoto para migración:
  - limpio (sin cambios pendientes)
  - `HEAD == origin/main`
- Se añadió ignore explícito en raíz:
  - `_publish_repo/`
- Se eliminaron referencias vivas operativas en docs/scripts principales (sin tocar `AGENTS.md`).
- Con esto `_publish_repo` ya no es requerido para flujo operativo futuro.

## `users_prueba.txt`

- No se abrió su contenido.
- Verificación:
  - `git ls-files -- users_prueba.txt` → sin salida (no trackeado en la raíz Git actual)
- `.gitignore` actualizado para ignorarlo.
- Se añadió `users_prueba.example.txt` con formato ficticio seguro.

## `tree_filtrado.txt`

- Verificación:
  - `git ls-files -- tree_filtrado.txt` → sin salida (no trackeado en la raíz Git actual)
- `.gitignore` actualizado para ignorar `tree_filtrado.txt` raíz.
- Se preserva referencia histórica en `docs/archive/extracted-txt/tree_filtrado.txt`.

## Cambios en `.gitignore`

Se añadieron/ordenaron reglas para:

- `_publish_repo/`
- `tree_filtrado.txt`
- `users_prueba.txt`, `token.txt`, `.env`, `.env.*`
- `viru.db`, `*.sqlite`, `*.sqlite3`
- `node_modules`, `npm-cache`, `.venv`, `venv`, `.next`, `.next_broken_*`, `.pytest_cache`, `__pycache__`, `logs`, `test-results`, `tmp`, `%TEMP%`, `_bench_before`, `_bench_after`

## Script creado/modificado

- Creado: `scripts/tree-clean.ps1`
- Modos soportados:
  - `.\scripts\tree-clean.ps1 -Mode repo`
  - `.\scripts\tree-clean.ps1 -Mode docs`
  - `.\scripts\tree-clean.ps1 -Mode live-docs`
- Comportamiento:
  - no genera `tree_filtrado.txt` en raíz por defecto
  - salida por archivo solo si se pasa `-OutputPath`
  - excluye `_publish_repo` y ruido local/generado

## Referencias a `_publish_repo` retiradas del flujo vivo

Actualizado para no depender de `_publish_repo`:

- `README.md` (sección de publicación segura)
- `docs/reference/done-checklist.md`
- `scripts/install-git-hooks.ps1`
- `scripts/release_guard.ps1`

En reportes históricos de `docs/reports/` se añadió nota posterior sin reescribir historia:

- `docs/reports/docs-sanitize-audit.md`
- `docs/reports/docs-sanitize-final-report.md`
- `docs/reports/docs-sanitize-qc-report.md`

## Comandos ejecutados (resumen)

- `git -C ... status --short`
- `git -C ... remote -v`
- `git -C ... rev-parse HEAD`
- `git -C ... rev-parse origin/main`
- `git init`
- `git remote add origin ...`
- `git fetch <ruta_local__publish_repo> main`
- `git ls-files -- users_prueba.txt`
- `git ls-files -- tree_filtrado.txt`
- `git check-ignore -v _publish_repo users_prueba.txt tree_filtrado.txt`
- `powershell -File .\scripts\tree-clean.ps1 -Mode repo|docs|live-docs`

## Validaciones

- La raíz real ahora contiene `.git`.
- `_publish_repo` queda ignorado por `.gitignore`.
- `users_prueba.txt` no trackeado en la raíz Git.
- `tree_filtrado.txt` de raíz no trackeado en la raíz Git.
- `scripts/tree-clean.ps1` ejecuta en los 3 modos.
- No se tocó `AGENTS.md`.
- No se reestructuró `/docs`.

## Estado final de Git (raíz)

- Rama: `main`
- Remote: `origin -> https://github.com/javiruu/viru-tracker.git`
- Referencia remota local disponible: `origin/main = bac86841d405ffc0dc36d5cef80037aecf91dc56`
- Working tree: contiene cambios no trackeados (esperable en esta migración; no se publicó en esta pasada).

## Riesgos pendientes

- Se detectó divergencia grande entre contenido local actual y el commit de referencia `main` (`bac86841...`); no se forzó sobrescritura para evitar pérdida de trabajo local.
- Falta completar la reconciliación final y publicación (commit/push) en una pasada controlada posterior.
- Borrado físico de `_publish_repo` debe ser manual, después de confirmar que no queda ningún proceso externo apuntándolo.

## Conclusión operativa

`_publish_repo` ya puede considerarse obsoleto para el flujo activo y **puede eliminarse manualmente** cuando quieras, con bajo riesgo operativo, porque la raíz ya está preparada para ser el único punto de trabajo.
