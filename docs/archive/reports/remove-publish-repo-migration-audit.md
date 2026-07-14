# Remove `_publish_repo` Migration Audit

Fecha: 2026-05-11

> Nota de normalizacion (2026-07-14): los identificadores de marca, rutas y remoto se alinearon con Viru Air durante el rebranding global. La evidencia literal original permanece en el commit `23c6daedf7f8ac0bd492bfbe011daf260cac93a6`.

## Estado detectado

- Repo actual detectado: `C:\Users\javiru\Desktop\viru-air\_publish_repo`
- Raíz real con `.git`: no (`C:\Users\javiru\Desktop\viru-air` no es repo Git)
- `_publish_repo` limpio: sí (sin cambios versionados pendientes)
- `origin` de `_publish_repo`: `https://github.com/javiruu/viru-air.git`
- Último commit local (`HEAD`): `bac86841d405ffc0dc36d5cef80037aecf91dc56`
- `origin/main`: `bac86841d405ffc0dc36d5cef80037aecf91dc56`
- Estado de sincronía: `HEAD == origin/main`

## Riesgos identificados

- La raíz real contiene archivos y carpetas locales que podrían chocar con archivos trackeados al enlazarla con `origin/main` si no se verifica antes.
- Existen artefactos sensibles/locales en rutas del workspace que deben permanecer fuera de Git.
- Hay reglas históricas que referencian `_publish_repo` y deben retirarse de documentación viva y scripts para evitar recaídas del flujo antiguo.

## Archivos/rutas sensibles detectados (solo nombre/ruta)

Sin abrir contenido:

- `C:\Users\javiru\Desktop\viru-air\users_prueba.txt`
- `C:\Users\javiru\Desktop\viru-air\viru.db`
- `C:\Users\javiru\Desktop\viru-air\backend\.env`
- `C:\Users\javiru\Desktop\viru-air\bot_ryanair_referencia_no_tocar\.env`
- `C:\Users\javiru\Desktop\viru-air\bot_ryanair_referencia_no_tocar\token.txt`
- `C:\Users\javiru\Desktop\viru-air\tree_filtrado.txt`

## Plan exacto de migración

1. Inicializar Git en la raíz real y apuntar a `origin` actual.
   - Verificación: `git remote -v`, rama activa y capacidad de `fetch` desde `origin/main`.
2. Comprobar conflictos antes de cualquier operación destructiva.
   - Verificación: listar archivos de `origin/main` y comparar contra archivos existentes en raíz; si hay conflicto destructivo, detener.
3. Completar bootstrap seguro de `main` en la raíz real.
   - Verificación: raíz con `.git`, `git rev-parse HEAD == git rev-parse origin/main`.
4. Endurecer exclusiones locales en `.gitignore`.
   - Verificación: `_publish_repo/`, `users_prueba.txt`, `tree_filtrado.txt` y artefactos locales quedan ignorados sin duplicados.
5. Destrackear artefactos si están versionados.
   - Verificación: `git ls-files -- users_prueba.txt tree_filtrado.txt` vacío en raíz.
6. Crear/actualizar `scripts/tree-clean.ps1` con modos `repo`, `docs`, `live-docs`.
   - Verificación: ejecutar los 3 modos y confirmar salida limpia sin `_publish_repo` ni caches.
7. Eliminar referencias vivas a `_publish_repo` (sin tocar `AGENTS.md` en esta pasada).
   - Verificación: búsqueda en `README.md`, `docs/**/*.md`, `scripts/**/*.ps1`, `scripts/**/*.py`.
8. Validación final integral y reporte de cierre.
   - Verificación: estado Git, remotos, commit actual, ignore efectivo, script funcional y riesgos pendientes.
