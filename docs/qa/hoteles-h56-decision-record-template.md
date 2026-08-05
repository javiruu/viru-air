# H56 — Plantilla de `DecisionRecord`

**Estado:** `evidence_incomplete`  
**Tipo:** plantilla de decisión; no es una aprobación  
**Fuente de verdad:** [H56 — revisión anual, providers, costes y siguiente roadmap](../reference/backend/hoteles-revision-anual-roadmap-h56.md)  
**Paquete asociado:** [plantilla de revisión anual H56](hoteles-h56-annual-review-template.md)  
**Fecha:** 2026-08-05  

> No completar una decisión con “parece bien”. Una decisión válida necesita evidencia ejecutada, scope, owner, approver, fecha efectiva, expiración y rollback/exit path. Si falta algo, conservar `evidence_incomplete`, `blocked` o `unknown`.

---

## 1. Registro vacío inicial

```text
decision_id: TBD-opaque
review_id: TBD-opaque
scope: product | provider | market | capability | flag | experiment | code | cost
subject: TBD
state: evidence_incomplete
evidence_refs: []
observed_period: TBD
known_unknowns: []
risk_summary: TBD
owner: TBD
approver: TBD
effective_at: TBD
expires_at: TBD
rollback_or_exit_path: TBD
follow_up_ticket: TBD
next_review_at: TBD
```

### Estados de decisión válidos cuando haya evidencia

Los estados persistidos son:

- `renew_promote`: continuar o ampliar solo el alcance demostrado;
- `remediate_throttle`: mantener limitado mientras se corrige;
- `pause_contain`: detener la superficie sin borrar históricos;
- `sunset_deprecate`: retirar con migración y comunicación;
- `reject_keep_fixture`: no abrir producción; conservar Mock/fixtures/manual.

`evidence_incomplete` y `blocked` son estados de trabajo de esta plantilla y no equivalen a una decisión de negocio final.

---

## 2. Checklist antes de aprobar

### Evidencia

- [ ] El periodo, entorno, commit y schema/config revision están identificados.
- [ ] Cada claim tiene fuente, timestamp, muestra, denominador y policy version.
- [ ] Se separan `measured`, `approximate`, `not_measured`, `contract_only` y `unknown`.
- [ ] Los datos fixture/demo, QA, provider off y canary están excluidos o segmentados.
- [ ] Los cambios de instrumentación, flags, provider y schema están anotados.

### Producto y confianza

- [ ] El efecto sobre búsqueda, decisión, tracking, retorno y soporte está medido o declarado no medido.
- [ ] Freshness, provenance, comparabilidad, estados degradados y copy son honestos.
- [ ] No hay regresión P0/P1 de ownership, privacidad, accesibilidad, coste o veracidad.

### Provider/mercado/coste

- [ ] Capability y exclusiones están verificadas por scope.
- [ ] Cuota, latencia, errores, retries y coste tienen fuente; unknown no se trata como cero.
- [ ] H54 autoriza el alcance de mercado y H53 respalda identidad/matching.
- [ ] Existe kill switch, owner, budget y rollback/exit path.
- [ ] Terms/privacy/deeplink/consent están revisados cuando aplican.

### Flags, experimentos y deuda

- [ ] Todos los entrypoints relevantes obedecen la decisión efectiva.
- [ ] No se elimina un flag/adaptor que sea kill switch, rollback o compatibilidad legacy.
- [ ] Experimentos tienen exposure real, denominador, SRM/novelty y guardrails.
- [ ] Personalización no altera órdenes objetivas ni usa señales comerciales ocultas.
- [ ] Monetización separa clicks, bookings, stays, refunds y ledger reconciliado.

### Gobierno

- [ ] Owner ejecutor y approver son personas/equipos concretos.
- [ ] Hay fecha efectiva y expiración/revisión.
- [ ] Existe acción correctiva con ticket y fecha si el estado no es `renew_promote`.
- [ ] Existe decisión explícita de no hacer o aplazar cuando corresponda.
- [ ] El siguiente roadmap se crea y enlaza solo después de aprobar las decisiones.

---

## 3. Primera decisión recomendada para completar

No aprobar aún un provider comercial. El primer `DecisionRecord` real debería cubrir una de estas decisiones acotadas, en este orden:

1. **Provider Makcorps:** confirmar `remediate_throttle` o `reject_keep_fixture` únicamente después de revalidar H07 con evidencia de cuota, 429, mapping, coste y condiciones.
2. **Worker hotelero:** confirmar `pause_contain`/`remediate_throttle` mientras el deployment Kubernetes siga siendo placeholder y no exista drill H55 pasado.
3. **Instrumentación H04:** decidir `remediate_throttle`/`blocked` hasta que la allowlist y dedupe hoteleros existan.
4. **Una flag concreta:** conservar, deprecar o eliminar solo tras enumerar lectores API/worker/job directo y sus tests.

Esto es una priorización de trabajo, no una decisión ya aprobada.

---

## 4. Resultado actual

```text
decision_id: not_created
state: evidence_incomplete
provider_approval: none
market_approval: none
cost_approval: none
next_roadmap_approval: none
reason: first evidence pack has not been executed and reviewed
```

**Regla:** no cambiar este estado hasta ejecutar el paquete H56, adjuntar evidencia redacted y obtener aprobación explícita.
