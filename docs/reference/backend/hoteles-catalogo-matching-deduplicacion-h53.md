# H53 — Calidad de catálogo, matching y deduplicación avanzada

**Estado:** COMPLETA como contrato de datos/calidad; implementación de resolución avanzada, cola de revisión, merge/split, migración y QA pendientes  
**Fecha:** 2026-08-05  
**Área:** backend / DB / catálogo / providers / producto / soporte / seguridad / QA  
**Fuente de verdad:** sí para resolver, medir, revisar y corregir la identidad de propiedades hoteleras de `/hoteles`  
**Fase del roadmap:** H53  
**Depende de:** H07, H10, H11, H12, H38, H39, H41, H44, H45, H52  
**Relacionado con:** H05 freshness/provenance/confidence, H06 provider-neutral, H08 onboarding, H15 resultados, H17 ranking, H19 precio, H20 comparación, H22 favoritos/tracking, H23 oferta real, H25 confianza, H35 privacidad/deeplinks

**Handoff:** [H54 — mercado nuevo con criterios de entrada y salida](../../plans/2026-08-04-hoteles-master-roadmap.md#fase-h54--mercado-nuevo-con-criterios-de-entrada-y-salida)

> H53 evita que varios nombres del mismo hotel parezcan propiedades distintas y evita, con la misma intensidad, fusionar hoteles diferentes por similitud superficial. La identidad canónica debe ser útil para búsqueda, tracking y métricas, pero toda corrección destructiva o ambigua debe ser explicable, reversible y auditable.

---

## 1. Propósito y decisión de alcance

La identidad hotelera tiene varias capas que no deben confundirse:

```text
registro externo del provider
        ↓
alias provider + evidencia de mapping
        ↓
propiedad canónica de Viru
        ↓
oferta/estancia/snapshot comparable
        ↓
favorito o tracking privado del usuario
```

H53 define cómo recorrer la primera mitad de esa cadena. No convierte un `provider_hotel_id` en un ID global, no usa la popularidad para decidir identidad y no trata un precio como evidencia suficiente de que dos propiedades son la misma.

### 1.1. Dentro de H53

- Identidad canónica de `HotelProperty` y alias externos.
- Normalización de nombre, ciudad, dirección y geodata.
- Candidate generation/blocking para no comparar todo el catálogo sin límites.
- Matching determinista cuando existe evidencia fuerte.
- Scoring explicable con señales positivas, negativas y datos faltantes.
- Umbrales separados para confirmar, revisar y rechazar.
- Cola de casos ambiguos y revisión humana o regla aprobada.
- Propuestas de merge/split sin sobrescribir evidencia original.
- Versionado de reglas, score, fuentes y decisiones.
- Reconciliación segura con favoritos, tracking, snapshots, alertas, inbox y feedback H52.
- Métricas de precisión, recall, falsos merges, falsos splits, backlog y cobertura geográfica.
- Privacidad, redaction, ownership, abuso, rollback y QA.

### 1.2. Fuera de H53

- No selecciona un nuevo provider comercial ni aprueba mercados por sí sola.
- No inventa IDs externos como GIATA, Booking, Expedia u otros si no están presentes y licenciados.
- No convierte geocoding en prueba de identidad inequívoca.
- No hace merge automático por similitud textual única.
- No muta una reserva, precio, fee o condición por corregir la identidad de un hotel.
- No decide ranking, comisión, afiliación ni personalización.
- No expone una consola de administración o un endpoint público sin auth, ownership y auditoría.
- No borra hoteles, aliases, snapshots o feedback originales como “limpieza”.
- No promete cobertura completa de un país o ciudad por tener geodatos.

---

## 2. Baseline real y límites actuales

### 2.1. Capacidades observables hoy

El repositorio ya contiene una base V1 concreta:

- `HotelProperty` guarda `canonical_name`, `normalized_name`, dirección opcional, ciudad, país, latitud, longitud y estrellas.
- `HotelProviderAlias` relaciona `(provider, provider_hotel_id)` con un `hotel_id`, guarda nombre/dirección/payload interno y `confidence_score`, y tiene unicidad por provider e ID externo.
- `HotelNormalizationService` normaliza texto con minúsculas, eliminación de acentos/puntuación y espacios; ciudad usa esa misma normalización y país se convierte a mayúsculas.
- `HotelMappingService` limita candidatos al país y calcula una puntuación heurística por nombre, ciudad y distancia Haversine.
- El umbral actual distingue `HIGH_CONFIDENCE_THRESHOLD=0.80`, `MEDIUM_CONFIDENCE_THRESHOLD=0.55` y margen de empate `0.05`.
- Un match alto sin runner-up cercano reutiliza la propiedad; una coincidencia media o ambigua crea una nueva propiedad y la marca como ambigua en el resultado de mapping.
- La ingestión consulta primero alias existente y, si no existe, usa mapping y persiste el alias.
- **Riesgo actual importante:** aunque `HotelMappingService` marque una coincidencia como ambigua, la ingestión V1 persiste `HotelProviderAlias` sin un estado explícito de `pending/ambiguous`; una ingestión posterior puede encontrar ese alias y reutilizarlo como si fuera inequívoco. H53 debe cerrar este flujo antes de habilitar matching avanzado o tracking dirigido.
- Los tests existentes cubren match alto, score bajo, score medio ambiguo, empate alto, unicidad del alias, ingestión y persistencia de payload interno.
- `HotelGeoService` usa coordenadas y Haversine para sugerencias de cercanía; eso sirve para distancia, no demuestra identidad.
- H07 y H10 ya documentan la diferencia entre ID interno y provider ID, y el riesgo de pasar `HotelProperty.id` a un adapter que necesita el ID externo.
- H44 proporciona fixtures y perfiles de fallo para desarrollo/QA; no convierte fixtures en verdad de catálogo.
- H52 ya clasifica `duplicate_hotel`, `hotel_identity_wrong`, `catalog_identity` y `catalog_mapping` como señales que deben llegar a H53 sin merge automático.

### 2.2. Lo que todavía no se demuestra

No hay evidencia suficiente de que el sistema actual tenga:

- una entidad de decisión de matching persistida y versionada;
- un grafo de identidad o tabla de candidatos entre propiedades;
- blocking multi-paso para catálogos grandes;
- señales de teléfono, dominio web, postal code, chain o amenities normalizadas;
- una cola de revisión con actor, motivo, permisos y SLA aprobado;
- estados persistentes `confirmed`, `ambiguous`, `rejected`, `pending` para alias;
- merge/split reversible con ledger append-only;
- detección de conflictos cuando un mismo alias apunta a dos propiedades;
- backfill, shadow compare o dry-run de una corrección masiva;
- métricas verificadas de precision, recall, falsos merges o falsos splits por mercado;
- reconciliación implementada para favoritos, tracking, snapshots, alertas e inbox después de un merge/split;
- un contrato de retención/redaction específico para payloads raw usados como evidencia.

Por tanto, el mapping heurístico V1 no se presenta como “matching avanzado” ni como un catálogo deduplicado. H53 cierra la política y deja explícita la deuda de implementación.

---

## 3. Vocabulario e invariantes

### 3.1. Identidades separadas

| Objeto | Significado | Puede ser ID global entre providers |
|---|---|---:|
| `provider_hotel_id` | Identificador de un provider dentro de su namespace | no |
| `HotelProviderAlias` | Relación observada entre provider ID y propiedad Viru | no |
| `HotelProperty.id` | Identidad interna de una propiedad canónica | solo dentro de Viru |
| `match_candidate_id` | Caso/version de comparación entre registros | no |
| `merge_operation_id` | Decisión auditada de consolidación | no |
| `offer_fingerprint` | Identidad de una oferta/estancia/condiciones | no es identidad de hotel |

Un mismo texto, coordenada o provider ID no puede cambiar estas fronteras por inferencia.

### 3.2. Invariantes de catálogo

- `(provider, provider_hotel_id)` es único en aliases.
- Un alias confirmado apunta a como máximo una propiedad canónica activa.
- Una propiedad puede tener muchos aliases de distintos providers.
- Un provider ID de un namespace no se compara como igual al de otro namespace sin evidencia explícita.
- Un merge no borra la identidad histórica: crea relación `merged_into` o equivalente.
- Un split puede restaurar los miembros/relaciones previos sin perder snapshots ni feedback.
- Un hotel con datos incompletos puede existir como `needs_review`; incompletitud no prueba duplicación.
- Geodata ausente no implica hoteles diferentes; geodata cercana no implica el mismo hotel.
- `confidence_score` de identity/matching no es confidence de precio, freshness o disponibilidad.
- El catálogo canónico no contiene `user_id`, thresholds privados, alertas, notas ni datos de ownership.
- Correcciones de identidad no reescriben el contenido factual de snapshots originales.

### 3.3. Estados objetivo

```text
property: active | quarantined | retired | needs_review
alias: pending | confirmed | ambiguous | rejected | superseded
candidate: proposed | needs_review | accepted | rejected | deferred
operation: proposed | dry_run | approved | applied | rolled_back | superseded
```

Los nombres son contrato de dominio; la implementación puede usar enums o strings allowlisted, pero no debe devolver estados arbitrarios sin documentación.

---

## 4. Normalización y procedencia

### 4.1. Campos normalizados

Cada fuente puede conservar su valor raw limitado y una representación normalizada separada:

| Campo | Normalización mínima | Riesgo si se usa solo |
|---|---|---|
| nombre | Unicode/acento, case, puntuación, espacios, tokens | hoteles con nombres de marca/sucursal similares |
| ciudad | alias lingüístico y acentos bajo vocabulario aprobado | barrios o ciudades homónimas |
| país | ISO-3166 allowlisted | datos del provider erróneos |
| dirección | abreviaturas, ordinales, números y componentes separados | hoteles en edificios cercanos |
| postal code | formato local, sin inventarlo | ausencia o formato provider |
| lat/lon | precisión, fuente, timestamp y validación | centroides/geocoder aproximado |
| teléfono | E.164 si hay base legal y dato fiable | números centrales de cadena |
| dominio | host normalizado y verificado | micrositios, cadenas y redirects |
| brand/chain | vocabulario explícito | franquicias con nombres parecidos |

La normalización nunca elimina la procedencia. Si un provider entrega `raw_address`, el sistema no debe presentar la dirección normalizada como dato confirmado sin conservar fuente y estado.

### 4.2. Redaction y minimización

No se usa como feature de matching por defecto:

- nombre de huésped, email, teléfono personal o reserva;
- notas privadas, mensajes, token, API key o headers;
- payload completo en dashboards o analytics;
- coordenadas exactas de una persona o domicilio privado;
- URLs con sesión, atribución o secreto.

Un teléfono público del hotel, dominio público o dirección comercial solo puede entrar en matching si el contrato de datos, retención y procedencia lo permite. Las evidencias para revisión se redacted y se acceden con mínimo privilegio.

---

## 5. Candidate generation y límites de coste

Comparar cada propiedad con todas las demás no es una estrategia aceptable cuando crece el catálogo. H53 requiere blocking por varias pasadas, con presupuesto y trazabilidad.

### 5.1. Bloques permitidos

Un candidato puede generarse por uno o más bloques:

- mismo país + ciudad normalizada;
- mismo prefijo postal cuando el dato exista y sea fiable;
- geohash o celda geográfica a precisión documentada;
- tokens significativos de nombre + ciudad;
- provider alias conocido o referencia explícita de mapping;
- dominio/teléfono normalizado cuando su uso esté aprobado.

Cada candidato guarda `candidate_generation_rule` y versión. No se usa un bloque como decisión final.

### 5.2. Protección anti-explosión

- Límite de candidatos por registro y por lote.
- Fan-out y tiempo máximos por provider/mercado.
- Procesamiento por lotes reanudable e idempotente.
- No lanzar geocoder externo por cada candidato.
- Cachear únicamente datos públicos y permitidos, con TTL y redaction.
- Si se supera el presupuesto, marcar `deferred`/`needs_review`; no elegir arbitrariamente el primer resultado.
- Registrar cantidad de candidatos descartados por límite para poder medir recall potencial.

### 5.3. Reconciliación de aliases

Antes de crear o reutilizar un alias:

1. buscar exacto `(provider, provider_hotel_id)`;
2. si existe `confirmed`, reutilizarlo sin reabrir automáticamente;
3. si existe `ambiguous/pending`, **no tratarlo como confirmado**, no reutilizarlo para tracking dirigido y enviarlo a revisión;
4. si V1 ha persistido un alias sin estado después de un mapping ambiguo, migrarlo a `pending`/`ambiguous` mediante backfill conservador antes de habilitar nuevos refreshes;
5. si el mismo provider ID trae datos incompatibles, crear conflicto revisable;
6. no sustituir un alias confirmado por el último payload sin auditoría.

El adapter/ingestion no puede resolver esta ambigüedad solo por encontrar una fila de alias. La decisión debe incluir el estado del alias, la policy version y la evidencia del mapping.

---

## 6. Scoring explicable y decisión por niveles

### 6.1. Señales

El score debe poder descomponerse en señales versionadas, por ejemplo:

```text
name_similarity
city_match
country_match
address_similarity
postal_match
geo_distance_bucket
phone_match
website_match
brand_consistency
provider_explicit_link
negative_conflicts
missing_evidence
```

El contrato no fija todavía pesos universales. Cada peso/transformación debe vivir en una `matching_policy_version`, tener fixtures y poder reproducirse. No introducir una librería o modelo externo sin aprobación de arquitectura, coste, privacidad y salida.

### 6.2. Hard negatives

Una señal positiva nunca debe superar ciertos conflictos sin revisión. Como mínimo:

- países incompatibles;
- ciudades claramente distintas sin evidencia de alias geográfico;
- distancia incompatible con la precisión de la fuente;
- códigos postales o direcciones contradictorias fuertes;
- dos sucursales/edificios explícitamente distintos;
- chain/brand que contradice el nombre y la dirección;
- provider ID ya confirmado para otra propiedad;
- datos de fixture mezclados con live sin compatibilidad de entorno.

Un hard negative produce `rejected` o `needs_review` según el caso; no se “compensa” con un nombre parecido.

### 6.3. Tres zonas de decisión

| Zona | Decisión | Consecuencia |
|---|---|---|
| `high` | propuesta de confirmación automática solo si no hay hard negative | puede crear/confirmar alias bajo policy y auditoría |
| `review` | caso ambiguo | no merge; cola de revisión o regla explícita |
| `low` | no-match provisional | mantener separado y permitir reabrir con nueva evidencia |

Los umbrales son configuración versionada, no números mágicos escritos en varios módulos. La política debe exigir margen entre primer y segundo candidato; un score alto con empate sigue siendo revisión.

### 6.4. Explicación mínima

Cada decisión debe poder responder:

- qué registros se compararon;
- qué policy/version se usó;
- qué señales dieron soporte;
- qué conflictos existieron;
- qué datos faltaban;
- quién o qué regla decidió;
- cuándo se decidió;
- qué downstream se verá afectado.

La explicación para soporte debe ser humana y redacted; la explicación técnica completa queda restringida.

---

## 7. Cola de revisión y ownership

### 7.1. Caso de revisión

El caso debe contener, como mínimo:

```text
match_candidate_id
left_record_ref / right_record_ref
provider namespaces
candidate_generation_rule
matching_policy_version
score + score_breakdown redacted
hard_negatives
state
priority
owner
created_at / updated_at
review_deadline solo si SLA aprobado
resolution_reason
```

No debe guardar secretos ni exponer IDs privados del usuario. Un reporte H52 se vincula mediante referencia opaca y ownership validado.

### 7.2. Roles

- **Catalog owner:** mantiene vocabulario y calidad canónica.
- **Provider owner:** valida semántica e IDs del provider.
- **DB/Backend:** implementa persistencia, migración e integridad.
- **Support/Product:** aporta casos H52 y contexto de impacto.
- **Security/Privacy:** revisa evidencia sensible y accesos.
- **QA:** prueba falsos merges, splits, rollback y downstream.

Quien propone una corrección P0/P1 no debe ser la única aprobación de la misma corrección. Los permisos de lectura y decisión se separan.

### 7.3. Priorización

Priorizar por riesgo e impacto, no solo por volumen:

1. ownership/privacy/security o tracking cruzado;
2. merge que contamina muchos snapshots, alertas o usuarios;
3. provider ID en conflicto;
4. duplicados en mercados activos y resultados visibles;
5. falsos splits que impiden encontrar/seguir el hotel;
6. casos de copy o mejora sin impacto material.

No se descarta un caso porque provenga de una sola persona si hay riesgo P0/P1.

---

## 8. Merge, split y ledger auditable

### 8.1. Propuesta antes de aplicar

Toda operación masiva o destructiva pasa por:

```text
proposed → dry_run → approved → applied
                         ↘ rolled_back
```

El dry-run debe listar:

- propiedades afectadas;
- aliases que cambiarían de destino;
- favoritos/watchlist afectados;
- tracked offers, snapshots y alertas relacionadas;
- comp sets e inbox/deeplinks potencialmente afectados;
- impacto estimado por mercado/provider;
- conflictos y registros que quedan `needs_review`;
- policy/version, actor y timestamp.

### 8.2. Merge seguro

Un merge no elimina físicamente las propiedades de origen en el primer release. Debe:

- elegir un canonical survivor con razón registrada;
- crear relación `merged_into`/equivalente versionada;
- mantener aliases y procedencia histórica consultables;
- actualizar relaciones futuras con una operación idempotente;
- evitar que un snapshot antiguo parezca observado bajo una identidad nueva sin marca;
- revisar tracking/favoritos/alertas privados con ownership del usuario;
- recalcular agregados solo con job versionado y resultado comparable;
- dejar rollback probado.

Un merge que afecte datos privados no puede ejecutarse solo por una señal pública de catálogo.

### 8.3. Split seguro

Un split se usa cuando una identidad canónica contiene propiedades distintas:

- conservar el nodo original y crear nuevos nodos con referencias de origen;
- repartir aliases solo cuando exista evidencia suficiente;
- dejar casos dudosos en `needs_review`, no adivinar;
- no copiar snapshots o tracking a ambos hoteles sin una relación de procedencia;
- reconstruir índices y resultados de manera idempotente;
- recalcular alertas solo después de validar la nueva identidad;
- comunicar una corrección al usuario sin revelar otros usuarios.

### 8.4. Ledger append-only

Cada propuesta, aprobación, aplicación y rollback guarda:

```text
operation_id
operation_type: merge | split | alias_reassign | quarantine | restore
policy_version
input_refs
output_refs
actor_type / actor_ref
reason_code
before_hash / after_hash
created_at
applied_at
rollback_of
redacted_evidence_ref
```

El ledger no se edita para “arreglar” el pasado. Una corrección posterior crea una nueva entrada.

---

## 9. Impacto downstream y protección del usuario

### 9.1. Favoritos y tracking

- Un favorito apunta a una propiedad canónica; tras merge debe resolverse con alias histórico sin cambiar silenciosamente la intención.
- Un tracking es una oferta/estancia privada, no solo un hotel; el merge no autoriza a cambiar habitación, fechas, provider o condiciones.
- Si la identidad deja de ser inequívoca, el tracking se marca `needs_review`/`unavailable` y no recibe snapshot nuevo hasta resolver.
- Nunca se mezclan historiales de dos ofertas solo porque el hotel canónico coincida.
- Las operaciones deben comprobar ownership por `user_id` y no usar `hotel_id` como autorización.

### 9.2. Rates, snapshots y alertas

- El snapshot original conserva su `hotel_id`/alias/observed_at` y referencia de mapping de aquel momento.
- Un cambio de canonical identity no crea una bajada/subida artificial.
- Una alerta pendiente se pausa o marca `not_evaluable` si el baseline deja de ser comparable.
- El sistema no emite una alerta de “hotel nuevo” solo por cambiar la identidad interna.
- H25/H26/H27 reciben reason codes y estados explícitos; no se oculta la corrección bajo `empty`.

### 9.3. Feedback H52

- `duplicate_hotel` y `hotel_identity_wrong` crean o agrupan casos H53 con referencias opacas.
- Un caso H52 permanece visible como señal individual aunque se agrupe en un cluster.
- La resolución H53 devuelve estado y explicación adecuados, no una promesa de que toda la historia se reescribió.
- La severidad privacy/security prevalece sobre la optimización de catálogo.

---

## 10. Métricas de calidad

Cada métrica necesita mercado, provider, ventana, policy version, denominador y método de muestreo.

### 10.1. Matching

- **Precision de merges confirmados:** matches correctos / merges revisados o gold set.
- **Recall de identidad:** duplicados conocidos correctamente enlazados / duplicados del gold set.
- **False merge rate:** pares de propiedades distintas fusionados / merges aplicados.
- **False split rate:** misma propiedad mantenida separada / pares equivalentes del gold set.
- **Alias conflict rate:** provider IDs con conflicto / aliases observados.
- **Ambiguity rate:** candidatos enviados a revisión / registros procesados.
- **Auto-decision rate:** decisiones automáticas / decisiones totales, siempre junto a precision.

### 10.2. Catálogo y experiencia

- propiedades duplicadas por mercado/provider;
- resultados repetidos en una misma búsqueda;
- hoteles sin geodata válida;
- hoteles con alias sin propiedad activa;
- propiedades con demasiados aliases incompatibles;
- búsquedas donde el hotel esperado no aparece por falso split;
- tracking/inbox afectados por identidad ambigua;
- tiempo de triage y resolución de casos H52/H53;
- operaciones aplicadas, rolled back y pendientes;
- coste/latencia de candidate generation y revisión.

No publicar precision/recall como hecho si solo existe el score heurístico V1 y no hay gold set o revisión representativa.

### 10.3. Gold set y muestreo

Antes de optimizar umbrales debe existir un conjunto etiquetado por mercado que incluya:

- mismos hoteles con nombres/acentos/idiomas distintos;
- cadenas con sucursales cercanas;
- hoteles homónimos en ciudades distintas;
- cambios de dirección o coordenadas imprecisas;
- provider IDs conflictivos;
- propiedades con datos ausentes;
- fixtures y payloads malformados;
- ejemplos H52 confirmados y falsos positivos.

El gold set debe tener procedencia, versión, reviewers y redaction. No copiar datos privados de reservas.

---

## 11. Migración y rollout

### H53-A — Contratos internos

- Crear tipos/enums para alias, candidate, policy, decisión y operación.
- Reutilizar `HotelNormalizationService` y `haversine_km` sin duplicar helpers.
- Definir serialización canónica y hashes opacos.
- Añadir validadores de país, coordenadas, provider namespace y estados.

### H53-B — Shadow matching

- Ejecutar la nueva política contra fixtures y una muestra redacted sin cambiar resultados públicos.
- Comparar contra mapping V1: matches, nuevos candidatos, conflictos y coste.
- Guardar divergencias y casos que requieren revisión.
- No escribir merge/split aplicado en modo shadow.

### H53-C — Cola y revisión

- Persistir candidatos y decisiones con ownership de operador.
- Añadir dedupe de casos y reapertura segura.
- Probar auth, redaction, paginación, rate limit y auditoría.
- Definir quién puede confirmar, rechazar, mergear, splittear o rollbackear.

### H53-D — Correcciones acotadas

- Empezar por aliases aislados y fixtures de bajo impacto.
- Usar dry-run y canary por provider/mercado.
- No tocar tracking activo sin plan de reconciliación y rollback.
- Medir downstream antes de ampliar.

### H53-E — Promoción

Solo promocionar una policy si:

- precision mínima aprobada por mercado está demostrada;
- false merge rate está dentro del límite de seguridad aprobado;
- conflictos y casos ambiguos no se ocultan;
- rollback se ha ejecutado con éxito en staging/canary;
- H52/H41/H45 tienen evidencia de integración;
- H54 recibe capacidades y límites por mercado.

---

## 12. Tests y evidencia de cierre

### Unitarios

- normalización determinista de acentos, punctuation, espacios y Unicode;
- normalización no borra procedencia ni convierte vacío en dato válido;
- mismo provider ID en dos aliases viola unicidad;
- provider IDs de namespaces distintos no colisionan;
- score desglosado reproduce la decisión con la misma policy version;
- hard negatives bloquean merge aunque el nombre sea idéntico;
- empate/runner-up cercano queda `needs_review`;
- missing geodata no se trata como distancia cero;
- coordenadas lejanas reducen elegibilidad sin borrar el registro;
- candidate generation respeta límites y es reanudable;
- merge/split no modifica snapshots originales;
- rollback restaura relaciones anteriores;
- fingerprints no incluyen `user_id`, email o secretos.

### Integración

- ingestión reutiliza solo alias confirmado;
- un mapping ambiguo no se persiste como alias confirmado y un alias legacy sin estado se pone en cuarentena/se hace backfill a `pending` antes de reutilizarse;
- alias ambiguo no permite refresh dirigido;
- provider ID conflictivo crea caso de revisión;
- mapping V1 y shadow H53 registran divergencia sin cambiar resultados;
- merge dry-run enumera favoritos, tracking, snapshots, alertas y comp sets afectados;
- aplicación idempotente no duplica relaciones;
- split conserva procedencia y no copia un snapshot a dos propiedades sin marca;
- tracking ambiguo no actualiza `current_price` ni dispara alerta;
- H52 duplicate report se agrupa sin perder la señal individual;
- 404/403 no revela propiedades o casos ajenos;
- payloads, evidencias y logs están redacted.

### QA y release

- catálogo con nombres equivalentes, cadenas cercanas y homónimos;
- ciudades con acentos, idiomas y aliases;
- geodata ausente, centroides aproximados y coordenadas erróneas;
- provider live, mock, partial, stale, error y payload drift;
- dark/light no aplica al backend, pero las superficies de revisión y feedback pasan H40;
- canary, rollback, métricas H41 y runbook H42/H45;
- no regresión de búsqueda, favoritos, tracking, histórico, alertas, inbox o deeplinks;
- artefactos redacted: fixtures, decision records, traces y métricas agregadas.

### Gate H53

H53 puede declararse implementada solo cuando:

1. la identidad interna y los aliases externos están separados y versionados;
2. la ingestión no convierte un mapping ambiguo en alias confirmado por persistencia implícita y los aliases legacy ambiguos quedan en `pending/ambiguous`;
3. matching usa señales explicables, hard negatives y umbrales con revisión;
4. existe gold set o evidencia equivalente para medir precision/recall y falsos merges;
5. los casos ambiguos tienen cola, owner, permisos y estados auditables;
6. merge/split pasa dry-run, ledger append-only, migración idempotente y rollback;
7. snapshots, ofertas y condiciones no se mezclan por accidente al corregir identidad;
8. favoritos, tracking, alertas, inbox y feedback conservan ownership y contexto;
9. privacidad, redaction, abuso y rate limits pasan H35/H38;
10. H41/H42/H45 aportan observabilidad, incidentes, canary y recuperación;
11. la promoción está limitada por mercado/provider y H54 recibe la matriz de cobertura.

**Estado de cierre documental:** contrato aprobado; la implementación futura debe marcar cada capacidad como `planned`, `implemented` o `verified`. El mapping heurístico actual permanece V1 y no constituye por sí solo un catálogo deduplicado.
