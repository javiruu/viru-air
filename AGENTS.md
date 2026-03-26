# AGENTS

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

