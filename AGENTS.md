# AGENTS

## Reglas operativas estables

- Usa `AGENTS.md` para reglas cortas del repo y `docs/reference/codex-operating-contract.md` para la politica operativa larga.
- Toma `docs/overview/`, `docs/reference/`, `docs/specs/`, `docs/ui/`, `docs/runbooks/` y `docs/qa/` como documentacion viva.
- Usa `docs/plans/` y `docs/archive/` solo como contexto historico cuando la documentacion viva no baste.
- Evita duplicar contratos o reglas en varios sitios: consolida una fuente canonica y enlazala.
- No hagas redisenos amplios de producto o arquitectura visual sin direccion explicita.
- Si cambias contratos de backend, rutas, datos o comportamiento sensible, deja evidencia clara y actualiza la documentacion canonica que corresponda.
- Antes de publicar cambios en GitHub, prepara resumen, archivos clave, riesgos, rollback y validacion manual si el impacto lo requiere.
- Publica cambios del repo usando la skill de GitHub correspondiente.
- Cierre automatico: toda tarea de codigo que no sea diagnostico-only debe terminar en commit + push a `main` dentro de `_publish_repo`.
- Antes de declarar "done", ejecuta la checklist `docs/reference/done-checklist.md` y usa la plantilla `docs/reference/final-report-template.md`.
- Nunca pongas secretos en markdown, commits, PRs, capturas o logs.
- Para QA E2E o bugs que no se reproduzcan bien con scripts, prioriza TestSprite si el bootstrap del repo ya se ejecuto en esa maquina.
- La configuracion canonica de TestSprite vive en `mcp.json`; no dupliques `API_KEY` ni la config del servidor en artefactos temporales o reportes.
- Para capturas UI y evidencia visual reutilizable, usa `docs/runbooks/runbook-ui-captures.md` como guia canonica.
- Si una conversacion requiere un flujo nuevo de capturas, actualiza ese runbook (seccion "Recetas") y reutiliza scripts estables `frontend/scripts/qa_capture_*`.
- En esta maquina, la carpeta visible `C:\Users\javiru\Desktop\viru-tracker` puede ser una copia de trabajo sin `.git`; el checkout Git real para publicar vive en `C:\Users\javiru\Desktop\viru-tracker\_publish_repo`.
- Antes de afirmar que "no hay git" o que no se puede publicar, comprueba `C:\Users\javiru\Desktop\viru-tracker\_publish_repo\.git` y ejecuta los comandos Git/publicacion desde ese checkout real si existe.
- Si el chat se abrio en la carpeta padre sin `.git`, trata `_publish_repo` como fuente canonica para `git status`, `commit`, `push` y verificaciones de rama/HEAD.
- Tras publicar cambios hechos en `_publish_repo`, sincroniza esos mismos archivos de vuelta a la carpeta visible `C:\Users\javiru\Desktop\viru-tracker`.
- Si una verificacion clave se bloquea por dependencias faltantes del entorno (por ejemplo `pytest`, `fastapi` u otras del runtime de backend/tests), dedica tiempo a instalar y dejar operativo ese entorno antes de cerrar el trabajo; no cierres la tarea solo reportando que faltan paquetes.
- Cuando el usuario pida copiar o tomar como referencia fuerte una UI externa, no la rebajes a una version sobria por defecto. En Viru, prioriza conservar la ambicion visual, riqueza compositiva y pulido del referente, adaptandolo al sistema del producto sin volverlo generico o plano.

## Busqueda segura en este repo

Para evitar salidas gigantes al buscar terminos como `playwright`, usar este comando por defecto:

```powershell
rg -n "<termino>" -S . `
  -m 80 `
  -g "!**/node_modules/**" `
  -g "!**/dist/**" `
  -g "!**/build/**" `
  -g "!**/coverage/**" `
  -g "!**/.next/**" `
  -g "!**/logs_ia/**" `
  -g "!**/fases/_extraido_txt/**" `
  -g "!**/*lock*.json" `
  -g "!**/pnpm-lock.yaml" `
  -g "!**/yarn.lock"
```

Ejemplo:

```powershell
rg -n "playwright" -S . `
  -m 80 `
  -g "!**/node_modules/**" `
  -g "!**/dist/**" `
  -g "!**/build/**" `
  -g "!**/coverage/**" `
  -g "!**/.next/**" `
  -g "!**/logs_ia/**" `
  -g "!**/fases/_extraido_txt/**" `
  -g "!**/*lock*.json" `
  -g "!**/pnpm-lock.yaml" `
  -g "!**/yarn.lock"
```
