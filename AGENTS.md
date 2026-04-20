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
- Nunca pongas secretos en markdown, commits, PRs, capturas o logs.
- En esta maquina, algunos chats pueden arrancar desde `C:\Users\javiru\Desktop\viru-tracker`, que es una copia visible sin `.git`; el checkout Git canonico para publicar es esta carpeta `_publish_repo`.
- Si un agente informa que "no hay git" en la carpeta padre, debe reubicar las operaciones de Git/publicacion a este checkout antes de concluir que no puede hacer `commit` o `push`.

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
