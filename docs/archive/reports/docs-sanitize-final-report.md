# Informe final de saneamiento documental

**Estado:** final  
**Última revisión:** 2026-05-11  
**Fuente de verdad:** no  
**Área:** documentación

## Resumen ejecutivo

Se consolidó `docs/` como centro documental del proyecto, se limpió la raíz de documentación legacy, se separó QA vivo de histórico, se archivaron duplicados que competían con fuentes canónicas y se regeneró el inventario documental completo.

## Objetivo del trabajo

Sanear, adaptar, deduplicar, clasificar y estructurar la documentación del repositorio sin tocar código funcional y sin exponer contenido sensible.

## Estructura antes

Antes del saneamiento, la documentación estaba repartida entre:

- raíz del repo con múltiples documentos legacy compitiendo con `docs/`;
- `docs/` con base razonable, pero todavía con duplicados en la raíz de `docs/`, material QA histórico mezclado con QA reutilizable y `DOCS_INVENTORY.md` desactualizado;
- `backend/docs/` duplicando contratos ya presentes en `docs/reference/backend/`;
- `fases/_extraido_txt/` duplicando transcripciones ya archivadas;
- `skills/` mezclando contexto IA útil con documentación externa no canónica para Viru.

## Estructura después

La estructura principal quedó organizada así:

- `docs/README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`
- `docs/overview/`
- `docs/product/`
- `docs/engineering/`
- `docs/reference/`
- `docs/specs/`
- `docs/ui/`
- `docs/runbooks/`
- `docs/qa/`
- `docs/prompts/`
- `docs/reports/`
- `docs/archive/`

Además:

- `docs/plans/` ahora separa `completed/`.
- la raíz quedó reducida a documentos de entrada reales y un único archivo sensible pendiente de revisión manual.

## Archivos creados

Principales archivos nuevos creados:

- `docs/README.md`
- `docs/overview/project-overview.md`
- `docs/overview/architecture-summary.md`
- `docs/engineering/backend.md`
- `docs/engineering/frontend.md`
- `docs/engineering/database.md`
- `docs/engineering/testing.md`
- `docs/engineering/infra.md`
- `docs/engineering/security.md`
- `docs/engineering/observability.md`
- `docs/product/dashboard.md`
- `docs/product/quick-search.md`
- `docs/product/watchlist.md`
- `docs/product/policies-page.md`
- `docs/prompts/README.md`
- `docs/plans/README.md`
- `docs/archive/duplicated/README.md`
- `docs/archive/old-reports/README.md`
- `docs/archive/extracted-txt/README.md`
- `docs/reports/docs-sanitize-audit.md`
- `docs/reports/docs-sanitize-final-report.md`

## Archivos modificados

Principales archivos actualizados:

- `README.md`
- `docs/INDICE_UNICO.md`
- `docs/DOCS_INVENTORY.md`
- `docs/qa/README.md`
- `docs/archive/README.md`
- `docs/archive/prompts/README.md`
- `docs/archive/qa/README.md`
- `docs/archive/root-legacy/README.md`
- `docs/overview/start-here.md`
- `docs/archive/tooling/testsprite/tmp/raw_report.md`

## Archivos movidos

Movimientos principales:

- raíz legacy a `docs/archive/root-legacy/`:
  - `DASHBOARD_REDESIGN_V2.md`
  - `UI_CHANGES.md`
  - `POLICIES_PAGE_COMPONENT_SPEC.md`
  - `POLICIES_PAGE_ACCEPTANCE_CHECKLIST.md`
  - `POLICIES_PAGE_COPY_DECK_ES.md`
  - `POLICIES_PAGE_REWRITE.md`
- duplicados de `docs/` raíz a `docs/archive/duplicated/`:
  - `docs/UI_CONTRACT_V1.md`
  - `docs/UI_SYSTEM_V1.md`
  - `docs/UI_VISUAL_QA_CHECKLIST.md`
  - `docs/estetica.md`
  - `docs/feature-flags.md`
  - `docs/quick-search-weather-policy.md`
- documentación backend duplicada a `docs/archive/duplicated/backend-docs/`
- reportes históricos a `docs/archive/old-reports/`
- `prompt.txt` raíz a `docs/prompts/legacy/prompt-root-legacy.txt`
- `tree_filtrado.txt` a `docs/archive/extracted-txt/tree_filtrado.txt`
- activos QA reubicados en:
  - `docs/qa/acceptance-checklists/`
  - `docs/qa/testsprite/`
  - `docs/qa/reports/`
  - `docs/qa/visual/`
- planes históricos a `docs/plans/completed/`

## Archivos fusionados

Consolidaciones efectivas por fuente de verdad:

- dashboard canónico en `docs/specs/product/dashboard-redesign-v2.md`
- cambios UI canónicos en `docs/specs/ui/ui-changes.md`
- policies canónicas en `docs/specs/policies/`
- quick search backend canónico en `docs/reference/backend/`
- UI system canónico en `docs/ui/`

## Archivos archivados

Familias archivadas o reforzadas como histórico:

- `docs/archive/root-legacy/`
- `docs/archive/duplicated/`
- `docs/archive/old-reports/`
- `docs/archive/extracted-txt/`
- `docs/archive/qa/`
- `docs/archive/prompts/`

## Archivos no tocados

Se dejaron sin cambios por seguridad o por no ser fuente de verdad del proyecto:

- `AGENTS.md`
- `users_prueba.txt`
- `fases/_extraido_txt/*`
- `skills/remodex/*`
- dependencias, caches, builds, entornos virtuales y `_publish_repo` durante el inventario principal

## Candidatos a eliminación manual

Pendientes recomendados para revisión humana:

- `users_prueba.txt`
- `fases/_extraido_txt/*.txt` porque duplican `docs/archive/fases/transcripts/`
- `skills/remodex/Docs/RECAP-local-first-cleanup.md` porque está vacío
- el resto de `skills/remodex/*` para decidir si deben seguir viviendo dentro del repo de Viru o documentarse como referencia externa

## Documentos marcados como sensibles

- `users_prueba.txt`

## Decisiones tomadas

- `docs/` queda como centro documental único.
- `docs/archive/` queda explícitamente separado de la ruta viva.
- `docs/qa/` conserva solo material reutilizable o activo.
- `docs/plans/` separa planes completados.
- `AGENTS.md` se mantiene como contrato operativo principal para agentes.
- los duplicados no compiten ya en la navegación principal.

## Contradicciones detectadas

- coexistían documentos raíz y documentos canónicos dentro de `docs/specs/`, `docs/reference/` y `docs/ui/`.
- `docs/DOCS_INVENTORY.md` tenía una taxonomía anterior que ya no representaba el repo real.
- `backend/docs/` seguía compitiendo con `docs/reference/backend/`.
- `docs/qa/` mezclaba histórico cerrado y QA reutilizable.

## Riesgos

- `fases/_extraido_txt/` sigue duplicando material histórico ya archivado.
- `skills/remodex/` sigue presente como documentación externa no canónica.
- `users_prueba.txt` requiere revisión manual y no debe tratarse como documentación del proyecto.
- algunas evidencias históricas archivadas conservan valor contextual, pero no deben reinterpretarse como estado actual.

## TODOs pendientes

- decidir si `fases/_extraido_txt/` se elimina o se mantiene como snapshot histórico adicional.
- decidir si `skills/remodex/` debe quedar fuera del inventario vivo del proyecto en una próxima pasada.
- valorar si `docs/qa/screenshots/`, `docs/qa/snapshots/` y `docs/qa/evidence/` necesitan una limpieza adicional o una README propia por subcarpeta.

## Comandos ejecutados

Comandos y familias de comandos usadas durante el saneamiento:

- `git -C ... status --short`
- `git -C ... branch --show-current`
- `git -C ... checkout -b docs/sanitize-documentation`
- inventario recursivo con PowerShell y Python estándar excluyendo ruido técnico
- `Get-ChildItem`, `Get-Content`, `Select-String`
- `robocopy` para reflejar `docs/` en `_publish_repo`
- validación local de enlaces Markdown con script Python sin dependencias externas

## Validaciones realizadas

Se validó:

- estado Git real en `_publish_repo`
- existencia de rama `docs/sanitize-documentation`
- inventario de `.md` y `.txt` excluyendo ruido
- conteo documental final: `184` documentos reales (`157 .md`, `27 .txt`)
- detección de duplicados por nombre y por hash durante la auditoría
- enlaces Markdown relativos en `README.md`, `AGENTS.md` y `docs/**/*.md`
- referencias a rutas antiguas en la documentación viva
- estructura final de `docs/`, `docs/qa/` y `docs/archive/`

## Validaciones no realizadas y motivo

- no se ejecutaron tests de aplicación porque la tarea fue documental y no tocó código funcional.
- no se eliminaron directamente `fases/_extraido_txt/*` ni `skills/remodex/*` porque requieren decisión humana adicional.

## Estado de git final

Estado esperado de cierre para publicación:

- rama de trabajo: `docs/sanitize-documentation`
- commit documental principal creado en `_publish_repo`
- integración posterior en `main` mediante fast-forward
- verificación final requerida: `local HEAD == origin/main`

## Próximos pasos recomendados

1. Revisar manualmente `users_prueba.txt` y decidir su destino fuera de la documentación del proyecto.
2. Decidir si `fases/_extraido_txt/` debe eliminarse por duplicidad histórica.
3. Decidir si `skills/remodex/` debe permanecer en el repo como referencia externa o salir del perímetro documental de Viru.
# Nota posterior: `_publish_repo` fue un artefacto local temporal usado durante el saneamiento documental. No forma parte del flujo actual ni debe usarse como fuente de verdad.
