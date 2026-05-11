# Auditoría inicial de saneamiento documental

**Estado:** auditoría inicial  
**Última revisión:** 2026-05-11  
**Fuente de verdad:** no  
**Área:** documentación

## Resumen ejecutivo

El repositorio ya tiene una primera consolidación documental en `docs/`, pero sigue conviviendo con:

- documentación raíz que compite con la canónica;
- duplicados exactos entre `docs/` y `docs/archive/`;
- duplicados funcionales entre `backend/docs/` y `docs/reference/backend/`;
- transcripciones históricas duplicadas entre `fases/_extraido_txt/` y `docs/archive/fases/transcripts/`;
- un `docs/DOCS_INVENTORY.md` existente pero desactualizado respecto al estado real;
- ausencia de `docs/README.md`;
- material sensible o potencialmente sensible que no debe entrar en consolidaciones (`users_prueba.txt`).

Hallazgo operativo relevante:

- `C:\Users\javiru\Desktop\viru-tracker` no está inicializado como repo Git.
- El repo versionado real para publicación está en `C:\Users\javiru\Desktop\viru-tracker\_publish_repo`.
- La rama de trabajo requerida se ha creado en `_publish_repo`: `docs/sanitize-documentation`.

## Comandos ejecutados

```powershell
git -C "C:\Users\javiru\Desktop\viru-tracker\_publish_repo" status --short
git -C "C:\Users\javiru\Desktop\viru-tracker\_publish_repo" branch --show-current
git -C "C:\Users\javiru\Desktop\viru-tracker\_publish_repo" checkout -b docs/sanitize-documentation

Get-ChildItem -Force
Get-ChildItem -Force .. 
Get-ChildItem -Force . -Directory -Recurse -Depth 2 | Where-Object { $_.Name -eq ".git" }

python - <<'PY'
# inventario recursivo de .md/.txt con exclusión explícita de:
# node_modules, .venv, venv, .next, .next_broken_*, npm-cache,
# .pytest_cache, __pycache__, logs, test-results, tmp, %TEMP%,
# _bench_before, _bench_after, _publish_repo, .git,
# bot_ryanair_referencia_no_tocar
# con detección de:
# - conteos por zona
# - duplicados por nombre
# - duplicados por hash
# - posibles sensibles por patrón de nombre
PY

Get-Content README.md
Get-Content docs/INDICE_UNICO.md
Get-Content docs/DOCS_INVENTORY.md
Get-Content docs/overview/start-here.md
Get-Content docs/overview/current-state.md
Get-Content docs/overview/repo-map.md
Get-Content docs/reference/README.md
Get-Content docs/specs/README.md
Get-Content docs/qa/README.md
Get-Content docs/archive/README.md
```

## Mapa actual de documentación

Zonas activas detectadas:

- raíz del repo: documentación mezclada con entradas legacy;
- `docs/`: centro documental actual de facto;
- `docs/overview/`: onboarding y reentrada;
- `docs/reference/`: referencia técnica activa;
- `docs/specs/`: especificaciones activas;
- `docs/ui/`: sistema visual canónico;
- `docs/runbooks/`: operación;
- `docs/qa/`: QA reutilizable, pero con mucho histórico aún mezclado;
- `docs/archive/`: histórico ya parcialmente ordenado;
- `backend/docs/`: duplicados funcionales respecto a `docs/reference/backend/`;
- `fases/_extraido_txt/`: histórico/transcripciones;
- `skills/viru-tracker-context/`: contexto IA útil;
- `skills/remodex/`: documentación externa/ajena al producto, no fuente de verdad de Viru.

## Conteo de documentos

Conteo limpio tras excluir ruido técnico:

- `.md`: 162
- `.txt`: 28
- total documental real detectado: 190
- documentos en raíz: 12
- documentos bajo `docs/`: 148
- documentos bajo `backend/docs/`: 2
- documentos bajo `frontend/docs/`: 0
- documentos bajo `fases/`: 11
- documentos bajo `prompts/`: 0
- documentos bajo `skills/`: 16
- documentos ya archivados bajo `docs/archive/`: 48
- documentos de QA/evidencia detectados por patrón: 78
- documentos potencialmente sensibles: 2

Distribución actual dentro de `docs/`:

- `overview/`: 3
- `adr/`: 3
- `reference/`: 8
- `runbooks/`: 7
- `specs/`: 7
- `ui/`: 4
- `qa/`: 31
- `plans/`: 27
- `archive/`: 48
- documentos sueltos en `docs/` raíz: 9

## Documentos en raíz

Documentos detectados en la raíz de trabajo:

- `AGENTS.md`
- `README.md`
- `COLOR_PALETTE_AUDIT.md`
- `DASHBOARD_REDESIGN_V2.md`
- `POLICIES_PAGE_ACCEPTANCE_CHECKLIST.md`
- `POLICIES_PAGE_COMPONENT_SPEC.md`
- `POLICIES_PAGE_COPY_DECK_ES.md`
- `POLICIES_PAGE_REWRITE.md`
- `UI_CHANGES.md`
- `prompt.txt`
- `tree_filtrado.txt`
- `users_prueba.txt`

Lectura inicial:

- `AGENTS.md` y `README.md` sí deben seguir siendo de entrada.
- El resto compite con documentación ya consolidada dentro de `docs/` o debe archivarse.

## Documentos vivos detectados

Se consideran vivos o próximos a canónico en el estado actual:

- `AGENTS.md`
- `README.md`
- `docs/INDICE_UNICO.md`
- `docs/overview/start-here.md`
- `docs/overview/current-state.md`
- `docs/overview/repo-map.md`
- `docs/reference/README.md`
- `docs/reference/backend/quick-search-contract.md`
- `docs/reference/backend/quick-search-acceptance-checklist.md`
- `docs/reference/quick-search-weather-policy.md`
- `docs/specs/README.md`
- `docs/specs/product/dashboard-redesign-v2.md`
- `docs/specs/ui/ui-changes.md`
- `docs/specs/policies/*.md`
- `docs/ui/UI_SYSTEM_V1.md`
- `docs/ui/UI_CONTRACT_V1.md`
- `docs/ui/UI_VISUAL_QA_CHECKLIST.md`
- `docs/ui/estetica.md`
- `docs/runbooks/*.md`
- `docs/adr/*.md`
- `docs/qa/README.md`

## Documentos históricos detectados

Claramente históricos o pensados para trazabilidad:

- `docs/archive/**`
- `fases/_extraido_txt/*.txt`
- `prompt.txt` y `docs/archive/prompts/prompt.txt`
- la mayor parte de `docs/plans/*.md`
- reportes fechados dentro de `docs/qa/`
- `tree_filtrado.txt` como snapshot generado del árbol

## Documentos duplicados o sospechosos de duplicidad

Duplicados funcionales claros:

- `DASHBOARD_REDESIGN_V2.md` vs `docs/specs/product/dashboard-redesign-v2.md`
- `UI_CHANGES.md` vs `docs/specs/ui/ui-changes.md`
- `POLICIES_PAGE_COMPONENT_SPEC.md` vs `docs/specs/policies/policies-page-component-spec.md`
- `POLICIES_PAGE_ACCEPTANCE_CHECKLIST.md` vs `docs/specs/policies/policies-page-acceptance-checklist.md`
- `POLICIES_PAGE_COPY_DECK_ES.md` vs `docs/specs/policies/policies-page-copy-deck-es.md`
- `POLICIES_PAGE_REWRITE.md` vs `docs/specs/policies/policies-page-rewrite.md`
- `backend/docs/quick-search-contract.md` vs `docs/reference/backend/quick-search-contract.md`
- `backend/docs/quick-search-acceptance-checklist.md` vs `docs/reference/backend/quick-search-acceptance-checklist.md`
- `docs/quick-search-weather-policy.md` vs `docs/reference/quick-search-weather-policy.md`
- `docs/UI_CONTRACT_V1.md` vs `docs/ui/UI_CONTRACT_V1.md`
- `docs/UI_SYSTEM_V1.md` vs `docs/ui/UI_SYSTEM_V1.md`
- `docs/UI_VISUAL_QA_CHECKLIST.md` vs `docs/ui/UI_VISUAL_QA_CHECKLIST.md`
- `docs/estetica.md` vs `docs/ui/estetica.md`

Duplicados exactos o casi exactos entre vivo e histórico:

- múltiples `docs/qa/*.md` replicados en `docs/archive/qa/...`
- todas las transcripciones `fases/_extraido_txt/*.txt` replicadas en `docs/archive/fases/transcripts/*.txt`

## Documentos potencialmente obsoletos

Primeros candidatos:

- `tree_filtrado.txt`
- `docs/changelog/*` si no está enlazado desde la navegación viva
- `docs/checks/*` si duplica QA o runbooks
- raíces legacy ya consolidadas en `docs/specs/` o `docs/ui/`
- reportes QA fechados que no sean reutilizables

## Documentos contradictorios o con versiones divergentes

Contradicciones/documentos divergentes detectados:

- `README.md` raíz sigue apuntando a una arquitectura documental anterior (`docs/reference`, `docs/qa`, etc.) pero no existe `docs/README.md`.
- `docs/DOCS_INVENTORY.md` existe con otra taxonomía (`canonical/reference/archived/ignored`) y ya no representa fielmente el inventario real requerido por esta refactorización.
- existen documentos raíz antiguos con encoding roto o menos metadatos que sus versiones consolidadas en `docs/specs/` y `docs/ui/`.
- `docs/qa/` mezcla material evergreen con reportes fechados que ya compiten con `docs/archive/qa/`.

## Documentos a fusionar

Objetivo de consolidación probable:

- preservar como canónicas las versiones ya normalizadas en `docs/specs/`, `docs/reference/` y `docs/ui/`;
- convertir los documentos raíz equivalentes en archivo histórico o duplicado archivado;
- decidir si `backend/docs/` se mantiene como referencia local del backend o se archiva por duplicar `docs/reference/backend/`;
- rehacer `docs/DOCS_INVENTORY.md` con tabla única y acciones propuestas;
- crear `docs/README.md` como punto de entrada operativo para humanos y agentes.

## Documentos a mover

Movimientos probables:

- documentos raíz legacy hacia `docs/archive/root-legacy/` o `docs/archive/duplicated/`;
- `prompt.txt` hacia `docs/prompts/legacy/` o archivo equivalente;
- reportes fechados de `docs/qa/` hacia `docs/archive/old-reports/` o `docs/archive/qa/` según el estado final deseado;
- posible reubicación de documentación QA viva a subcarpetas más explícitas;
- posible creación de `docs/prompts/`, `docs/engineering/`, `docs/product/` y `docs/reports/` si aporta claridad y se justifica con contenido real.

## Documentos a archivar

Candidatos muy fuertes:

- raíces duplicadas ya consolidadas en `docs/specs/` y `docs/ui/`
- `fases/_extraido_txt/*` si se conserva una sola ubicación histórica
- duplicados exactos entre `docs/qa/` y `docs/archive/qa/`
- `prompt.txt` raíz
- `tree_filtrado.txt`

## Documentos candidatos a eliminación manual

No se elimina nada en esta fase. Quedan como candidatos manuales tras consolidación y validación:

- `tree_filtrado.txt`
- copias exactas archivadas redundantes si quedan dos ubicaciones históricas equivalentes
- reportes generados no enlazados ni útiles para trazabilidad

## Documentos que NO se tocarán

Por seguridad o por estar fuera de alcance documental principal:

- `.env`
- `.env.*`
- `token.txt`
- `users_prueba.txt` en cuanto a contenido
- cualquier archivo con credenciales, dumps o datos personales si apareciera
- `bot_ryanair_referencia_no_tocar/`
- dependencias, caches, builds, venvs y outputs generados excluidos del inventario

## Riesgos

- Mezclar documentación viva con histórico si se mueve `docs/qa/` sin criterio fino.
- Romper enlaces internos desde `README.md`, `docs/INDICE_UNICO.md` o `docs/specs/README.md`.
- Archivar demasiado pronto material que hoy aún actúa como fuente de verdad informal.
- Duplicar otra vez el sistema si se crea nueva estructura sin reaprovechar la consolidación ya existente.
- Exponer o copiar contenido sensible si se abre `users_prueba.txt` o archivos similares.
- Confusión operativa por la dualidad `workspace` vs `_publish_repo` si no se mantiene trazabilidad en el informe final.

## Propuesta inicial de nueva arquitectura documental

En lugar de rehacer `docs/` por completo, la propuesta inicial es consolidar sobre la arquitectura ya existente y completar huecos:

- mantener y reforzar:
  - `docs/overview/`
  - `docs/adr/`
  - `docs/reference/`
  - `docs/specs/`
  - `docs/ui/`
  - `docs/runbooks/`
  - `docs/archive/`
- crear o actualizar:
  - `docs/README.md`
  - `docs/reports/`
  - `docs/prompts/`
  - `docs/engineering/` si hay suficiente contenido real consolidable
  - `docs/product/` si conviene separar visión funcional de specs de implementación
- racionalizar:
  - `docs/qa/` en material reutilizable solamente
  - `docs/plans/` separando activo/completado si el contenido real lo justifica
  - documentos sueltos en `docs/` raíz moviéndolos a su subdominio correcto

## Próximos pasos

1. Reescribir `docs/DOCS_INVENTORY.md` con tabla única y acciones propuestas por documento.
2. Decidir fuente de verdad por familia duplicada:
   - raíz vs `docs/specs/`
   - `backend/docs/` vs `docs/reference/backend/`
   - `docs/ui/` vs duplicados en `docs/` raíz
   - `docs/qa/` vs `docs/archive/qa/`
3. Crear `docs/README.md` y reorientar el `README.md` raíz.
4. Mover documentos raíz fuera de la entrada principal usando `git mv` cuando aplique en `_publish_repo`.
5. Reordenar prompts, QA e histórico sin perder trazabilidad.
6. Validar enlaces y generar informe final.
