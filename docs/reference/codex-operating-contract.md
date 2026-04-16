Status: reference
Scope: persistent operating contract for Codex sessions in Viru Tracker
Last reviewed: 2026-04-16
Canonical source: docs/reference/codex-operating-contract.md
Related: docs/reference/README.md, docs/overview/start-here.md, AGENTS.md

---
# Codex Operating Contract

## Purpose

Condensar el conocimiento operativo estable extraido del master document externo de Viru Tracker Studio y traducirlo a reglas que encajan con Codex y con este repo.

## Donde debe vivir cada tipo de conocimiento

- `AGENTS.md`: reglas cortas, recordatorios operativos y enlaces.
- `docs/reference/codex-operating-contract.md`: politica operativa adaptada a Codex.
- `docs/overview/`: reentrada rapida, estado actual y mapa del repo.
- `docs/reference/`, `docs/specs/`, `docs/ui/`, `docs/runbooks/`, `docs/qa/`: verdad de dominio, tecnica, UX y operacion.
- `docs/plans/` y `docs/changelog/`: referencia historica util.
- `docs/archive/`: ultimo recurso para reconstruir intencion historica, nunca primera parada.

## Source-of-truth hierarchy

1. Instrucciones activas del usuario y de la sesion.
2. `AGENTS.md` para reglas cortas obligatorias del repo.
3. Este documento para politica operativa persistente de Codex.
4. `docs/overview/` para reenganche y navegacion.
5. `docs/reference/`, `docs/specs/`, `docs/ui/`, `docs/runbooks/` y `docs/qa/` para verdad funcional.
6. `docs/plans/` y `docs/changelog/` para contexto historico cercano.
7. `docs/archive/` solo cuando los documentos vivos no explican una decision.

## Reglas estables adoptadas

- Toda tarea relevante debe tener objetivo, alcance, superficies afectadas y criterio de cierre.
- Un modulo o documento debe tener un proposito claro; evita caminos funcionales o documentales duplicados.
- El conocimiento estable debe quedar en archivos del repo o en una skill reusable, no solo en conversaciones.
- No rompas rutas, contratos API, estructuras de datos o reglas visuales base sin actualizar la fuente canonica correspondiente.
- Prioriza claridad, accesibilidad, estabilidad contractual y trazabilidad antes que pulido decorativo.
- Las skills deben ser de proposito unico, con entradas explicitas y salidas verificables.
- Secretos, tokens y datos sensibles no deben vivir en markdown, commits, PRs, comentarios, capturas ni logs compartidos.
- Los conectores o automatizaciones se tratan como superficies sensibles: activalos solo con owner claro, guardrails y rollback.

## Roles adaptados a Codex

| Modelo del Word | Equivalente en este entorno | Responsabilidad real |
|---|---|---|
| CEO / Product | usuario + alcance aprobado | prioridad, direccion y decisiones finales |
| Chief of Staff | plan aprobado + docs de apoyo | convertir la necesidad en tarea ejecutable |
| CTO / Head of Product Design | ADRs, specs, UI docs y razonamiento tecnico | criterios tecnicos y de UX |
| Implementation agent | Codex en el workspace | cambios locales y evidencia |
| Quality Gatekeeper | pasada explicita de review antes de publicar | detectar riesgos, regresiones y test manual |
| Git & Repo Manager | skill de GitHub / paso de publicacion | higiene de branch, PR y merge |
| Human validator | usuario | validacion manual o en servidor cuando aplique |

## Flujo adaptado de review y publicacion

1. Aterrizar scope usando request, `AGENTS.md` y documentacion viva.
2. Implementar localmente en el workspace controlado.
3. Preparar un review packet minimo: resumen, archivos clave, riesgos, rollback y test manual propuesto.
4. Revisar el cambio con foco en contratos, regresiones y huecos de evidencia.
5. Pedir o registrar validacion humana cuando el cambio toque comportamiento real, datos, auth, infra o riesgos visibles para usuarios.
6. Publicar mediante la skill de GitHub correspondiente, no como area de borrador sin validar.
7. Si cambia la fuente de verdad, actualizarla dentro del repo.

## Cuando exigir validacion manual humana

- Cambios en auth, sesion o permisos.
- Cambios en contratos API, esquemas, migraciones o retencion de datos.
- Cambios en infra, despliegue, variables de entorno, conectores o secretos.
- Cambios que afecten rutas core o flujos visibles para usuario.
- Acciones destructivas o de rollback sensible.

## Lo que no se porta de forma literal

- `COMPANY.md`, `TEAM.md`, `tasks/` y el arbol de compania de Paperclip.
- El org chart como estructura del repo.
- Budgets, heartbeats y activity logging como sistema formal dentro del repo.
- `HISTORY.md` como log obligatorio separado mientras la trazabilidad viva ya se apoya en GitHub y `docs/changelog/`.
- Fases de import y bootstrap exclusivas de Paperclip.

## Matriz Word -> Codex

| Bloque del Word | Decision | Destino en Viru Tracker |
|---|---|---|
| Principios no negociables | Adoptar | `AGENTS.md` + este documento |
| Regla de remote GitHub | Adaptar | este documento + PR template + skill de GitHub |
| Estructura de package y archivos Paperclip | Solo referencia | no se porta literal; se mapea a `docs/`, `AGENTS.md` y la skill global |
| Source-of-truth hierarchy | Adoptar | este documento + `AGENTS.md` |
| Org chart, autoridad y escalado | Adaptar | mapeo de roles y flujo de review/publicacion |
| Engineering pipeline, gatekeeper y repo manager | Adaptar | este documento + `.github/pull_request_template.md` |
| Skills, rutinas y heartbeats | Adaptar | skill global reusable y regla de skills pequenas |
| Budgets y niveles de autonomia | Solo referencia | se retiene como principio de cautela, no como capa formal |
| Connectors, secrets y plugins | Adoptar | este documento y practica operativa del repo |
| Runbooks y templates | Adaptar | uso de `docs/runbooks/`, `docs/qa/` y plantilla de PR |
| Import, rollout y fases de Paperclip | Solo referencia | contexto historico, fuera del runtime del repo |

## Uso recomendado

- Lee este documento cuando necesites traducir reglas de proceso a trabajo real en Codex.
- Si la duda es de producto, backend, UX o QA, vuelve a la documentacion viva especifica del area.
- Si una regla aparece repetida en tres o mas sitios, consolida una unica fuente y reemplaza el resto por enlaces.
