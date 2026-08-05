# H05 — Contrato de procedencia, freshness y confidence de hoteles

**Estado:** completo como contrato — pendiente de implementación gradual  
**Fecha:** 2026-08-04  
**Área:** backend / frontend / producto / QA  
**Fuente de verdad:** sí para la semántica de calidad de datos hoteleros; los campos actuales y las migraciones futuras deben adaptarse a este contrato sin romper compatibilidad.

## 1. Propósito

H05 define qué significa cada precio hotelero y qué puede prometer Viru al mostrarlo. La existencia de un `HotelRateSnapshot` no demuestra por sí sola que el precio sea actual, comparable o reservable.

El contrato separa cinco preguntas:

1. **Procedencia:** ¿de dónde salió el dato?
2. **Freshness:** ¿cuándo se observó y qué edad tiene?
3. **Disponibilidad:** ¿qué sabemos sobre si se puede reservar?
4. **Comparabilidad:** ¿representa la misma estancia y conocemos sus condiciones?
5. **Confidence:** ¿qué confianza merece la observación completa?

Estas dimensiones no deben colapsarse en una única píldora ambigua. Un precio puede ser reciente pero tener condiciones incompletas; puede ser barato pero poco confiable; puede venir de un provider real pero estar obsoleto; puede ser un fixture válido para tests pero nunca un dato live.

## 2. Diagnóstico de la base actual

### 2.1. Campos existentes reutilizables

| Superficie | Campo/estado actual | Lectura H05 |
|---|---|---|
| `HotelRateSnapshot` | `provider` | Identidad lógica del origen; no prueba frescura ni disponibilidad |
| `HotelRateSnapshot` | `provider_run_id` | Vincula la observación a una ejecución trazable |
| `HotelRateSnapshot` | `collected_at` | Timestamp actual de captura; se conserva como alias de compatibilidad |
| `HotelRateSnapshot` | `availability_status` | Estado de disponibilidad, pendiente de vocabulario canónico |
| `HotelRateSnapshot` | fechas, huéspedes, habitación, régimen, cancelación, moneda, importe | Base para comparar la estancia; faltan fees y algunos campos avanzados |
| `HotelProviderRun` | `running`, `completed`, `failed` | Trazabilidad operativa; `partial` debe añadirse en una fase posterior si el worker lo necesita |
| `HotelProviderAlias` | `confidence_score` | Confianza de matching de identidad provider → hotel; no es confianza del precio |
| `HotelAreaResolveOut` | `confidence`, `source` | Confianza y fuente del geocoder/área; no es confianza de la tarifa |
| Frontend `HotelRateOut` | `collected_at`, `availability_status`, `provider_run_id` | Información disponible para presentar; faltan campos explícitos de freshness/provenance/confidence |
| `assessHotelSignal` | `none`, `limited`, `scored` | Evaluación de paridad; no debe reutilizarse como freshness de precio |

### 2.2. Problemas actuales que H05 evita

1. `HotelProviderStatusPill` infiere una señal a partir de rates/paridad, pero no puede distinguir rate reciente de snapshot antiguo.
2. La UI muestra provider y hora de captura, pero no un estado canónico de freshness ni el motivo de una limitación.
3. `mock` puede producir snapshots técnicamente válidos con datos estáticos; eso no los convierte en live.
4. `confidence_score` del alias y `confidence` del área pueden confundirse con confianza de precio si se exponen sin namespace.
5. El sistema no tiene campos de fees/total final suficientes para afirmar comparabilidad completa en todos los casos.
6. `availability_status` acepta una cadena libre y no documenta todos los estados de provider/error.
7. `collected_at` describe persistencia local, no necesariamente el instante en que el partner verificó disponibilidad.
8. El sweep puede tener `HotelProviderRun` completado aunque una parte del universo no haya producido rates útiles; H09 debe ampliar la semántica operativa.

## 3. Vocabulario canónico

Los nombres de almacenamiento/API pueden evolucionar, pero los valores y significados deben permanecer estables.

### 3.1. `provenance_kind`

Indica el origen y el grado de intermediación del dato. No indica por sí solo si es actual.

| Valor | Significado | Copy permitido |
|---|---|---|
| `provider_observed` | Observación obtenida de una respuesta de provider para la estancia consultada | “Comprobado con [provider]” |
| `provider_revalidated` | Observación obtenida mediante refresh dirigido de una oferta trackeada | “Revisado para tu seguimiento” |
| `cache_current` | Respuesta reutilizada desde cache dentro de su TTL válido | “Dato reciente; última comprobación …” |
| `historical_snapshot` | Registro histórico conservado para evolución o comparación | “Histórico del …” |
| `fixture_demo` | Fixture/mock de desarrollo, QA o demo | “Datos de demostración” |
| `derived` | Valor calculado desde observaciones, por ejemplo mediana o señal agregada | “Calculado a partir de …” |
| `unknown` | No se puede demostrar la procedencia | “Procedencia no disponible” |
| `unavailable` | No existe observación válida que mostrar | “Sin precio comprobable” |

Reglas:

- `fixture_demo` nunca se presenta como `live`, aunque se haya leído hace segundos.
- `derived` siempre conserva referencias internas a las observaciones base cuando sea necesario auditarlo.
- `cache_current` no significa “precio confirmado por el partner ahora”.
- `historical_snapshot` no debe aparecer como opción actual sin un aviso de fecha.
- `unknown` y `unavailable` no se rellenan con un valor por defecto optimista.

### 3.2. `freshness_status`

Indica la edad y validez temporal de una observación para el contexto de uso. Es distinto de la procedencia.

| Valor | Significado | Regla base |
|---|---|---|
| `fresh` | Observación dentro del umbral corto del contexto y con timestamp válido | Puede mostrarse como “reciente” o “comprobado hace …”; nunca como garantía de reserva |
| `recent` | Observación válida pero fuera del umbral corto y dentro del TTL de uso | Mostrar hora/fecha; no usar lenguaje de “ahora” |
| `stale` | Observación superó el TTL operativo recomendado, pero sigue siendo útil como contexto | Mostrar advertencia y ofrecer reintento |
| `expired` | Observación demasiado antigua para guiar una decisión actual | No usar para afirmar precio actual; puede conservarse como histórico |
| `historical` | Observación solicitada o presentada como histórico, independientemente de su edad actual | Mostrar fecha y no mezclarla con actual sin etiqueta |
| `unknown` | Timestamp ausente, inválido o política no calculable | No presentar freshness positiva |

`freshness_status` no sustituye a `availability_status`. Un dato `fresh` puede tener disponibilidad `unknown`; un dato `recent` puede decir `sold_out`.

### 3.3. `availability_status`

Indica qué sabe Viru sobre disponibilidad de la oferta, no si el hotel existe.

| Valor | Significado |
|---|---|
| `available` | El provider devolvió una oferta válida para la estancia consultada |
| `limited` | El provider devolvió una señal parcial o con restricciones que impiden afirmar disponibilidad completa |
| `sold_out` | El provider indicó explícitamente que no hay disponibilidad para esa consulta |
| `unknown` | No hay confirmación suficiente |
| `provider_error` | El provider no pudo responder o su respuesta no pudo validarse |
| `not_requested` | La superficie solo muestra catálogo/histórico y no pidió disponibilidad |

`provider_error` es un resultado de la consulta, no un atributo permanente del hotel. No se debe convertir automáticamente en `sold_out` ni en lista vacía silenciosa.

### 3.4. `conditions_completeness`

Indica si las condiciones necesarias para comparar la tarifa están presentes.

| Valor | Significado |
|---|---|
| `complete` | Fechas, ocupación, habitación, régimen, cancelación, moneda e importe total aplicable están presentes o explícitamente resueltos |
| `partial` | Falta una o más condiciones relevantes, pero el dato puede servir como orientación |
| `unknown` | No se puede saber qué condiciones aplican |
| `not_applicable` | La observación no representa una oferta, por ejemplo un histórico agregado |

No se debe mostrar “mejor precio” entre ofertas con `conditions_completeness=partial` sin advertencia y política de comparabilidad.

### 3.5. `confidence_level`

Es una evaluación de la observación completa. No es una valoración del hotel, no es ranking y no es el `confidence_score` de matching o geocoder.

| Valor | Significado | Uso visible |
|---|---|---|
| `high` | Procedencia y timestamp válidos, estancia coincidente, condiciones suficientes y provider sin señales críticas de fallo | Puede mostrar señal positiva de confianza, sin prometer reserva |
| `medium` | Observación útil, pero con cache, condiciones parciales, historial corto o alguna limitación controlada | Mostrar limitación junto al precio |
| `low` | Dato incompleto, stale, provider degradado o matching/condiciones con dudas | No usar como claim fuerte de ahorro |
| `unavailable` | No existe base suficiente para evaluar | No mostrar score; explicar qué falta |

No se presenta un número al usuario como si fuera una probabilidad de reserva. Un score numérico interno, si se necesita, debe incluir `confidence_model_version` y no debe sustituir al nivel explicable.

## 4. Identidad temporal de una observación

### 4.1. Campos canónicos objetivo

```text
observed_at             instante en que el provider produjo o verificó la observación
persisted_at             instante en que Viru la guardó, si se necesita diferenciarlo
provider_run_id          ejecución o refresh que originó la observación
provider                 provider lógico
provenance_kind          origen/intermediación
freshness_status         edad calculada según política
availability_status      disponibilidad declarada o conocida
conditions_completeness  suficiencia de condiciones
confidence_level         confianza de la observación
confidence_model_version versión del cálculo, si existe score interno
```

### 4.2. Compatibilidad con el modelo actual

- `collected_at` se mantiene durante la migración y se interpreta como `observed_at` solo mientras no exista un timestamp más preciso.
- H10/H11 deben decidir si se añade `observed_at` y cómo se rellena desde `collected_at` sin reescribir históricos.
- Si el provider devuelve hora propia y Viru registra otra, ambas no deben mezclarse; conservar la procedencia de cada timestamp.
- Un `HotelProviderRun.finished_at` no sustituye a `observed_at` de cada rate.
- Un histórico sin timestamp válido recibe `freshness_status=unknown`, no `fresh`.

## 5. Política de freshness por contexto

Los TTL definitivos dependen de provider, mercado y scheduler. H05 fija defaults de contrato para que el sistema no invente estados; H07-H09 deben calibrarlos con evidencia.

### 5.1. Discovery/resultado de búsqueda

| Edad desde `observed_at` | Estado base | Copy orientativo |
|---|---|---|
| `0–30 min` | `fresh` | “Comprobado hace menos de 30 min” |
| `>30 min–6 h` | `recent` | “Comprobado hoy a las …” |
| `>6–24 h` | `stale` | “Puede haber cambiado; revisar de nuevo” |
| `>24 h` | `expired` | “Precio histórico; necesita una nueva comprobación” |

### 5.2. Tracking dirigido

El tracking no debe prometer periodicidad solo por existir un snapshot. Para una política inicial de comprobación horaria o diaria, se propone:

| Edad desde la última comprobación válida | Estado base | Acción |
|---|---|---|
| Dentro de la ventana esperada + gracia | `fresh` | Mostrar última revisión y próxima política |
| Hasta 2 ventanas esperadas | `recent` | Mostrar retraso moderado si aplica |
| Más de 2 ventanas y hasta 24 h | `stale` | Marcar seguimiento pendiente de revisión |
| Más de 24 h o sin sweep válido | `expired` | No disparar claim de bajada actual; alertar operación si corresponde |

H09 debe convertir “ventana esperada” en una configuración observable por provider y tracking. Si no hay scheduler garantizado, el UI debe decir que la última revisión ocurrió en una fecha concreta y no prometer “diario”.

### 5.3. Cache y fixtures

- Un cache dentro de TTL puede ser `fresh` o `recent`, pero `provenance_kind=cache_current` permanece visible para el sistema.
- Un fixture siempre conserva `provenance_kind=fixture_demo` y `freshness_status=unknown` o `historical` según el uso; nunca `fresh` en una superficie que pudiera parecer live.
- Un histórico puede estar almacenado recientemente y seguir siendo `fresh` en términos de persistencia, pero su semántica de negocio es `historical`; por eso `historical` tiene prioridad de presentación.
- Si el timestamp es posterior al reloj del servidor o está fuera de límites plausibles, se marca `unknown` y se registra warning técnico.

## 6. Cálculo de confidence

### 6.1. Separación de confianzas

El dominio debe mantener namespaces distintos:

```text
identity_confidence       matching de hotel/provider → HotelProperty
geocode_confidence        resolución de área → coordenadas
observation_confidence    calidad de la observación de precio/disponibilidad
comparability_confidence  posibilidad de comparar la estancia con otra
```

Una mejora del matching no puede convertir automáticamente una tarifa stale en confiable.

### 6.2. Evaluación determinista inicial

H05 propone un modelo explicable con cinco dimensiones internas de 0 a 100:

| Dimensión | Peso | Señales |
|---|---:|---|
| `freshness_score` | 30 % | edad, timestamp válido, TTL del contexto |
| `provenance_score` | 25 % | provider observado/revalidado, cache, histórico, fixture |
| `match_score` | 20 % | hotel, fechas, ocupación y moneda coinciden con la consulta |
| `conditions_score` | 15 % | habitación, régimen, cancelación, fees/total y disponibilidad |
| `provider_health_score` | 10 % | éxito reciente, warnings, timeout/429 y consistencia |

```text
observation_score =
  0.30 * freshness_score
+ 0.25 * provenance_score
+ 0.20 * match_score
+ 0.15 * conditions_score
+ 0.10 * provider_health_score
```

Umbrales iniciales:

- `high`: `>= 80` y ninguna dimensión crítica por debajo de 60.
- `medium`: `55–79` o una dimensión crítica entre 40 y 59.
- `low`: `1–54` o cualquier condición que impida comparar con seguridad.
- `unavailable`: no hay observación o faltan señales mínimas para calcular.

Estos números son una política inicial auditable, no una probabilidad estadística. H07/H41 pueden recalibrarlos, pero deben documentar versión, motivo y efecto en históricos.

### 6.3. Hard caps

Para evitar scores engañosos:

- `fixture_demo` → máximo `low` en UI de producto.
- `expired` o `unknown` freshness → máximo `low`.
- `provider_error` → `unavailable` para precio actual.
- `conditions_completeness=unknown` → máximo `low` para comparabilidad.
- moneda desconocida o estancia incompatible → `unavailable`.
- solo un provider no impide mostrar un precio, pero impide afirmar paridad o “mejor entre providers”.
- un rate barato no aumenta confidence por sí mismo.

## 7. Reglas de presentación al usuario

### 7.1. Qué debe aparecer junto al precio

En una card o detalle, cuando haya tarifa:

1. importe y moneda;
2. contexto de estancia: fechas y ocupación resumidas;
3. habitación/régimen/cancelación cuando estén disponibles;
4. freshness: fecha/hora de comprobación en locale;
5. procedencia en lenguaje humano si aporta confianza;
6. advertencia de fees o condiciones desconocidas;
7. estado de disponibilidad si no es `available`;
8. acción siguiente segura: revisar, reintentar, guardar o abrir partner.

### 7.2. Copy prohibido o condicionado

No usar:

- “precio final” si el partner puede modificarlo;
- “disponible ahora” sin una comprobación equivalente y reciente;
- “live” para cache, fixture, histórico o snapshot viejo;
- “garantizado”, “asegurado” o equivalentes;
- “mejor precio” sin misma estancia, moneda y condiciones comparables;
- “bajó X %” sin baseline válido y snapshots comparables;
- “seguimiento diario” si H09 no demuestra scheduler y última revisión.

### 7.3. Copy de estados

Los textos finales deben pasar por i18n, pero la semántica mínima es:

- `fresh`: “Comprobado recientemente”.
- `recent`: “Comprobado hoy a las …”.
- `stale`: “Este precio puede haber cambiado”.
- `expired`: “Precio histórico; vuelve a comprobarlo”.
- `fixture_demo`: “Datos de demostración; no representan disponibilidad real”.
- `partial`: “Faltan condiciones para compararlo del todo”.
- `unknown`: “No podemos confirmar la frescura de este dato”.
- `provider_error`: “El proveedor no respondió; no significa que esté agotado”.
- `unavailable`: “No hay un precio comprobable para esta estancia”.

## 8. Reglas para ranking, paridad y alertas

### Ranking

- Freshness y confidence pueden ser señales de elegibilidad o desempate, pero no deben ocultarse como si fueran precio.
- Un resultado barato con confidence low no debe aparecer como recomendación fuerte.
- El ranking debe poder explicar si descarta un resultado stale o no comparable.

### Paridad

- Paridad solo se calcula entre rates con fechas, ocupación, moneda y condiciones comparables.
- `provider_count` no equivale a `provider_count_comparable`.
- Un provider con error no se cuenta como provider caro ni barato.
- Si no hay dos observaciones comparables, el estado es `limited`, no `stable`.

### Alertas

- No disparar una alerta de bajada desde una observación `fixture_demo`, `expired`, `provider_error` o incompatible.
- La alerta debe conservar el snapshot que la originó, `provider_run_id`, freshness y condiciones comparadas.
- Una alerta puede indicar “cambio observado” aunque el precio final del partner no esté garantizado.
- Si la nueva observación es `unknown` o `partial`, no convertir la pérdida de datos en una falsa subida/bajada.

## 9. Contrato de API objetivo

H05 no obliga a cambiar todos los endpoints inmediatamente, pero los nuevos contratos deben evolucionar hacia un bloque explícito:

```json
{
  "amount": 125.0,
  "currency": "EUR",
  "provider": "makcorps",
  "observed_at": "2026-08-04T09:20:00Z",
  "collected_at": "2026-08-04T09:20:03Z",
  "provider_run_id": "opaque-run-id",
  "provenance": {
    "kind": "provider_observed",
    "provider": "makcorps"
  },
  "freshness": {
    "status": "fresh",
    "age_seconds": 420,
    "policy_version": "hotel-freshness-v1"
  },
  "availability": {
    "status": "available",
    "source": "provider"
  },
  "conditions": {
    "completeness": "partial",
    "room_known": true,
    "meal_plan_known": false,
    "cancellation_known": true,
    "fees_known": false
  },
  "confidence": {
    "level": "medium",
    "score": 72,
    "model_version": "hotel-observation-v1"
  }
}
```

Reglas de compatibilidad:

- Durante la transición se mantienen `collected_at`, `provider`, `provider_run_id` y `availability_status`.
- Los clientes antiguos no deben romperse si los bloques nuevos están ausentes; deben caer a `unknown`, nunca a `fresh`.
- No exponer `raw_payload` en respuestas públicas por defecto.
- Los IDs opacos no autorizan acceso a datos de otro usuario; ownership sigue siendo obligatorio.
- El score puede omitirse si no hay datos suficientes; no serializar `0` como si fuera una confianza calculada.

## 10. Contrato para providers y runs

H06/H07 deben ampliar el adapter para que pueda devolver, cuando exista:

- timestamp de observación;
- disponibilidad explícita;
- si el importe incluye impuestos/fees;
- habitación, régimen y cancelación;
- deeplink seguro sin secretos;
- warnings estructurados;
- razón de resultado parcial/vacío/error;
- capacidad de revalidación dirigida.

`HotelProviderRun` debe evolucionar en H09 para distinguir como mínimo:

```text
running
completed
partial
failed
skipped
```

Un run `completed` significa que terminó el proceso, no que todos los hoteles tengan tarifas válidas. Las cantidades deben separar items recibidos, rates válidos, rates descartados y errores si la operación lo necesita.

## 11. Migración y backfill

H10/H11 deben realizarlo de forma reversible:

1. Mantener columnas actuales y añadir campos nuevos como nullable.
2. Backfill `observed_at` desde `collected_at` cuando el valor sea válido.
3. Asignar `provenance_kind` desde provider: `mock` → `fixture_demo`; providers habilitados → `provider_observed` solo si la observación es realmente de consulta/provider.
4. Rates históricos sin evidencia suficiente → `historical_snapshot` y `confidence_level=low` o `unavailable`.
5. No convertir automáticamente todos los snapshots Makcorps en `high`; el provider no sustituye validación de condiciones.
6. Mantener `availability_status` desconocido si no existe señal explícita.
7. Registrar versión de política aplicada al backfill.
8. Probar rollback y clientes que todavía consumen el contrato antiguo.

## 12. Tests y evidencias requeridos

### Unitarios

- clasificación de freshness en límites exactos y zonas horarias;
- reloj adelantado/atrasado y timestamp nulo;
- fixture nunca marcado live/fresh de producto;
- provider error no convertido en sold out;
- cálculo de confidence y hard caps;
- condiciones incompletas reducen comparabilidad;
- paridad excluye rates incompatibles;
- alertas ignoran snapshots no elegibles;
- compatibilidad de payload antiguo y nuevo.

### Integración

- rate persistido conserva provider run y timestamp;
- área de búsqueda propaga estado sin inventarlo;
- tracked offer usa el último snapshot elegible;
- endpoint no expone raw payload ni datos ajenos;
- run parcial no se devuelve como éxito pleno;
- fallback mock queda rotulado como demo.

### Frontend

- cada estado tiene copy ES/EN;
- `fresh`, `recent`, `stale`, `expired`, `demo` y `unknown` no comparten color/copy engañoso;
- una tarifa sin freshness no muestra “live”;
- card y detalle enseñan contexto mínimo;
- lector de pantalla recibe estado, no solo color;
- loading y stale no provocan saltos o acciones imposibles.

### Operación

- logs estructurados incluyen provider, run, estado y duración, sin raw payload ni secretos;
- métricas separan provider error, stale, expired y unavailable;
- dashboard de H41 permite detectar provider degradado sin mirar datos personales;
- runbook explica cuándo reintentar y cuándo no declarar indisponibilidad.

## 13. Gate de H05

**Aprobado como contrato de calidad de datos.** H05 queda completo cuando:

- procedencia, freshness, disponibilidad, completitud y confidence tienen vocabulario separado;
- los TTL base y sus límites están documentados;
- fixture, cache, histórico, provider y error no se confunden;
- existe una política explicable de confidence con hard caps;
- el copy prohibido y permitido está claro;
- ranking, paridad y alertas respetan elegibilidad;
- migración/backfill y compatibilidad están definidos;
- tests y evidencias necesarios están enumerados;
- se documenta qué falta implementar en H06-H11 y frontend.

H05 **no afirma que estos campos ya estén implementados**. H06/H07/H09/H10/H11 y H13/H15/H16/H18/H23-H28 deben implementar sus partes y demostrar que ningún precio se presenta con más certeza de la que permiten los datos.
