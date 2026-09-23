# Documentaci�n de Viru Air

**Estado:** vivo  
**�ltima revisi�n:** 2026-09-22
**Fuente de verdad:** s�  
**�rea:** documentaci�n

## Resumen

`docs/` es el centro documental del proyecto. La regla general es simple:

- la documentaci�n viva debe vivir aqu�, cerca de su dominio;
- `docs/archive/` conserva hist�rico y trazabilidad;
- los prompts y contexto IA se documentan sin competir con `AGENTS.md`;
- las evidencias pesadas se guardan separadas de las specs y de la referencia viva.

## C�mo navegar esta carpeta

Empieza por:

1. [Indice �nico](INDICE_UNICO.md)
2. [Overview del proyecto](overview/project-overview.md)
3. [Estado actual](overview/current-state.md)
4. [Mapa del repo](overview/repo-map.md)

Login, Supabase, base de datos, JWT o conectividad local del API? Lee primero el
[Runbook Supabase nativo](runbooks/runbook-supabase-native.md) y la
[matriz de variables de entorno](architecture/environment.md).

## Qu� carpetas importan

- `overview/`: reentrada r�pida, estado actual y mapas de navegaci�n.
- `product/`: res�menes funcionales por �rea de producto.
- `engineering/`: res�menes t�cnicos por capa.
- `reference/`: contratos y referencias t�cnicas activas.
- `specs/`: especificaciones vivas.
- `ui/`: sistema visual y contrato UI.
- `runbooks/`: operaci�n y respuesta.
- `qa/`: QA reutilizable, evidencias activas y capturas vivas.
- `adr/`: decisiones de arquitectura.
- `plans/`: planes de trabajo; no son fuente de verdad de producto.
- `prompts/`: material para agentes y prompts antiguos organizados.
- `reports/`: auditor�as y reportes de saneamiento/documentaci�n.
- `archive/`: hist�rico. No es fuente de verdad activa.

## Documentaci�n viva vs hist�rica

Documentaci�n viva:

- describe comportamiento actual o proceso vigente;
- se enlaza desde `README.md`, `INDICE_UNICO.md` o docs por �rea;
- tiene una fuente de verdad identificable;
- evita logs, dumps y reportes de una sola sesi�n.

Documentaci�n hist�rica:

- conserva decisiones antiguas, fases, reportes cerrados o prompts legacy;
- puede contradecir la documentaci�n viva;
- debe vivir en `docs/archive/` o en `docs/prompts/legacy/`.

## C�mo decidir d�nde a�adir una nueva doc

- `product/`: visi�n funcional, flujos, comportamiento visible.
- `engineering/`: capa t�cnica resumida por dominio.
- `reference/`: contratos o tablas de referencia activas.
- `specs/`: requisitos de implementaci�n todav�a vigentes.
- `runbooks/`: operaci�n, recuperaci�n, despliegue, validaci�n.
- `qa/`: checklists vivas, cat�logos TestSprite, evidencia ligera y reportes �tiles.
- `adr/`: decisiones de arquitectura ya tomadas.
- `plans/`: trabajo pendiente o completado, pero no normativa viva.
- `prompts/`: prompts y contexto IA.
- `archive/`: hist�rico o duplicado preservado.

## Convenciones

- Usa `kebab-case` para nuevos documentos.
- Mant�n `README.md`, `AGENTS.md` y ADRs con sus convenciones propias.
- Cada doc viva debe incluir estado, fecha, fuente de verdad y �rea.
- Si un documento consolida otros, a�ade una secci�n `Fuentes consolidadas`.

## C�mo tratar evidencias pesadas

- Las capturas, snapshots y reportes JSON no deben mezclarse con specs.
- Evidencia activa y ligera: `docs/qa/visual/`, `docs/qa/reports/`, `docs/qa/evidence/`.
- Evidencia histórica o de ciclos cerrados: `docs/archive/qa-reports/`. Las carpetas históricas pesadas (`qa-evidence`, `qa-screenshots`, `qa-snapshots`, `qa-visual`) se purgaron el 2026-09-23 con aprobación del usuario.

## C�mo tratar prompts antiguos

- `AGENTS.md` es el contrato operativo principal para agentes.
- `docs/reference/codex-operating-contract.md` complementa reglas persistentes.
- Los prompts antiguos deben vivir en `docs/prompts/legacy/`.

## C�mo mantener el inventario

- Cada cambio documental relevante debe reflejarse en [DOCS_INVENTORY.md](DOCS_INVENTORY.md).
- Si se mueve una fuente de verdad, actualiza tambi�n:
  - `README.md`
  - `docs/INDICE_UNICO.md`
  - la doc relacionada por dominio

## Relacionado

- [README ra�z](../README.md)
- [Indice �nico](INDICE_UNICO.md)
- [Inventario documental](DOCS_INVENTORY.md)
- [Archivo hist�rico](archive/)
