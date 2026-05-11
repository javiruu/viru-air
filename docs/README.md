# Documentación de Viru Tracker

**Estado:** vivo  
**Última revisión:** 2026-05-11  
**Fuente de verdad:** sí  
**Área:** documentación

## Resumen

`docs/` es el centro documental del proyecto. La regla general es simple:

- la documentación viva debe vivir aquí, cerca de su dominio;
- `docs/archive/` conserva histórico y trazabilidad;
- los prompts y contexto IA se documentan sin competir con `AGENTS.md`;
- las evidencias pesadas se guardan separadas de las specs y de la referencia viva.

## Cómo navegar esta carpeta

Empieza por:

1. [Indice único](INDICE_UNICO.md)
2. [Overview del proyecto](overview/project-overview.md)
3. [Estado actual](overview/current-state.md)
4. [Mapa del repo](overview/repo-map.md)

## Qué carpetas importan

- `overview/`: reentrada rápida, estado actual y mapas de navegación.
- `product/`: resúmenes funcionales por área de producto.
- `engineering/`: resúmenes técnicos por capa.
- `reference/`: contratos y referencias técnicas activas.
- `specs/`: especificaciones vivas.
- `ui/`: sistema visual y contrato UI.
- `runbooks/`: operación y respuesta.
- `qa/`: QA reutilizable, evidencias activas y capturas vivas.
- `adr/`: decisiones de arquitectura.
- `plans/`: planes de trabajo; no son fuente de verdad de producto.
- `prompts/`: material para agentes y prompts antiguos organizados.
- `reports/`: auditorías y reportes de saneamiento/documentación.
- `archive/`: histórico. No es fuente de verdad activa.

## Documentación viva vs histórica

Documentación viva:

- describe comportamiento actual o proceso vigente;
- se enlaza desde `README.md`, `INDICE_UNICO.md` o docs por área;
- tiene una fuente de verdad identificable;
- evita logs, dumps y reportes de una sola sesión.

Documentación histórica:

- conserva decisiones antiguas, fases, reportes cerrados o prompts legacy;
- puede contradecir la documentación viva;
- debe vivir en `docs/archive/` o en `docs/prompts/legacy/`.

## Cómo decidir dónde añadir una nueva doc

- `product/`: visión funcional, flujos, comportamiento visible.
- `engineering/`: capa técnica resumida por dominio.
- `reference/`: contratos o tablas de referencia activas.
- `specs/`: requisitos de implementación todavía vigentes.
- `runbooks/`: operación, recuperación, despliegue, validación.
- `qa/`: checklists vivas, catálogos TestSprite, evidencia ligera y reportes útiles.
- `adr/`: decisiones de arquitectura ya tomadas.
- `plans/`: trabajo pendiente o completado, pero no normativa viva.
- `prompts/`: prompts y contexto IA.
- `archive/`: histórico o duplicado preservado.

## Convenciones

- Usa `kebab-case` para nuevos documentos.
- Mantén `README.md`, `AGENTS.md` y ADRs con sus convenciones propias.
- Cada doc viva debe incluir estado, fecha, fuente de verdad y área.
- Si un documento consolida otros, añade una sección `Fuentes consolidadas`.

## Cómo tratar evidencias pesadas

- Las capturas, snapshots y reportes JSON no deben mezclarse con specs.
- Evidencia activa y ligera: `docs/qa/visual/`, `docs/qa/reports/`, `docs/qa/evidence/`.
- Evidencia histórica o de ciclos cerrados: `docs/archive/qa/` o `docs/archive/tooling/`.

## Cómo tratar prompts antiguos

- `AGENTS.md` es el contrato operativo principal para agentes.
- `docs/reference/codex-operating-contract.md` complementa reglas persistentes.
- Los prompts antiguos deben vivir en `docs/prompts/legacy/` o `docs/archive/prompts/`.

## Cómo mantener el inventario

- Cada cambio documental relevante debe reflejarse en [DOCS_INVENTORY.md](DOCS_INVENTORY.md).
- Si se mueve una fuente de verdad, actualiza también:
  - `README.md`
  - `docs/INDICE_UNICO.md`
  - la doc relacionada por dominio

## Relacionado

- [README raíz](../README.md)
- [Indice único](INDICE_UNICO.md)
- [Inventario documental](DOCS_INVENTORY.md)
- [Archivo histórico](archive/README.md)
