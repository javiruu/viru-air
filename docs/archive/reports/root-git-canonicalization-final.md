# Root Git Canonicalization Final

Fecha: 2026-05-11  
Repo raíz: `C:\Users\javiru\Desktop\viru-tracker`

## Resumen

Se completó la canonización operativa de la raíz como único repo Git de trabajo.  
`_publish_repo` queda fuera del flujo operativo y puede eliminarse manualmente después.

## Qué se hizo

1. Se creó base local de `HEAD` en la raíz sin sobrescritura destructiva:
   - `git fetch origin main`
   - `git reset --mixed origin/main`
2. Se confirmó:
   - rama `main`
   - `HEAD` local existente
   - `HEAD == origin/main` antes de nuevos commits
3. Se mantuvo `users_prueba.txt` como archivo intencional del proyecto:
   - no se borró
   - no se destrackeó
   - no se sustituyó
4. Se mantuvo `_publish_repo/` ignorado por `.gitignore` y fuera del flujo.
5. Se reforzó `scripts/tree-clean.ps1` para ocultar en salida de árbol:
   - `.env`, `.env.*`, `token.txt`, `viru.db`, `*.sqlite`, `*.sqlite3`, `tree_filtrado.txt`
   - sin ocultar `users_prueba.txt`
6. Se conservaron reglas de ignore para artefactos locales/caches/builds/temporales.

## Verificaciones ejecutadas

- `git branch --show-current`
- `git rev-parse HEAD`
- `git rev-parse origin/main`
- `git status --short --ignored`
- `git ls-files -- users_prueba.txt`
- `git ls-tree -r origin/main -- users_prueba.txt`
- `git check-ignore -v _publish_repo`
- `powershell -ExecutionPolicy Bypass -File .\scripts\tree-clean.ps1 -Mode repo`
- `powershell -ExecutionPolicy Bypass -File .\scripts\tree-clean.ps1 -Mode docs`
- `powershell -ExecutionPolicy Bypass -File .\scripts\tree-clean.ps1 -Mode live-docs`

## Estado y criterio final

- `C:\Users\javiru\Desktop\viru-tracker` es el repo Git operativo para commits futuros.
- `_publish_repo` ya no debe usarse para commit/push.
- `_publish_repo` no se borró en esta pasada; puede eliminarse manualmente.
- `users_prueba.txt` se conserva por decisión del usuario.
- `AGENTS.md` no fue modificado en esta pasada.

## Nota de alcance

Hay cambios locales previos al trabajo de migración (frontend/docs y rutas históricas) que no forman parte de esta canonización y deben revisarse aparte antes de incluirse en futuros commits.
