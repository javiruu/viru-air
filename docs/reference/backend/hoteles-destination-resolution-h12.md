# H12 — Resolución robusta de destino hotelero

**Estado:** completa como contrato de destino; implementación de autocomplete y hardening pendientes  
**Fecha:** 2026-08-04  
**Área:** backend / frontend / búsqueda / geocoder / producto  
**Fuente de verdad:** sí para la semántica de destino, tipos, confianza, ambigüedad y fallback en `/hoteles`.

**Depende de:** [H03 — arquitectura de información](../product/hoteles-information-architecture-h03.md), [H04 — métricas y eventos](../product/hoteles-metrics-events-h04.md), [H05 — freshness/provenance/confidence](hoteles-freshness-provenance-confidence-h05.md), [H06 — contrato provider-neutral](hoteles-provider-neutral-contract-h06.md)  
**Relacionado con:** H10 modelo de estancia, H13 formulario/URL state, H14 filtros/orden, H15 contrato de resultados/paginación, H17 búsqueda, H35 privacidad y H41 observabilidad.

---

## 1. Propósito y decisión de fase

H12 define cómo convertir una entrada humana como “Madrid”, “Madrid Centro”, un aeropuerto, un landmark o una región en un destino de búsqueda hotelera verificable. El sistema debe reducir ambigüedad antes de llamar a providers de hoteles y debe conservar la procedencia de la resolución sin enseñar jerga técnica innecesaria.

### Decisión H12

**Usar primero catálogo/datos internos; usar un adapter de geocoder externo solo como fallback controlado; no lanzar una búsqueda ambigua automáticamente.**

- Una resolución contiene tipo, país, coordenadas, etiqueta visible, `confidence` y `source`.
- Una coincidencia ambigua devuelve opciones o requiere confirmación.
- Una resolución externa no se convierte en hotel ni en disponibilidad.
- El geocoder no recibe API keys, email, `user_id` ni payloads de búsqueda innecesarios.
- El fallback externo permanece sujeto a flag, cache, rate limit, timeout y redaction.
- La búsqueda de rates solo comienza después de una resolución válida y suficientemente confiable.

La fase no implementa todavía la paginación global ni el envelope de resultados de H15.

---

## 2. Estado actual comprobable

| Pieza | Comportamiento actual | Limitación H12 |
|---|---|---|
| `area_resolve` | intenta ciudades internas por `normalized_city`, calcula centroides y devuelve una sola resolución | no tiene lista de candidatos tipados ni ambigüedad rica |
| `HotelNormalizationService` | normaliza texto/city para búsquedas internas | no constituye por sí solo un catálogo de tipos geográficos |
| `geocode_city` | fallback Nominatim configurable | filtra principalmente `city`/`administrative`, fija `confidence=medium`, no ofrece autocomplete ni cache persistente |
| `/api/v1/hotels/area-resolve` | devuelve `area_label`, coordenadas, país, confidence y source | contrato mínimo; no expone `type`, `place_id`, bounding box ni warnings estructurados |
| frontend `useHotelSearch` | mantiene `areaResolved`, modo name/area y badge de resolución | no muestra candidatos tipados ni confirma ambigüedad antes del search |
| `HotelSearchPanel` | permite entrada de área y muestra sugerencia básica | no garantiza país/tipo para nombres duplicados |
| flags | `HOTEL_GEOCODER_ENABLED` y `NOMINATIM_URL/USER_AGENT` | no hay aún presupuesto/cache/cooldown contractualmente aplicado al geocoder |
| tests | cubren Madrid/Málaga, minúsculas, parcial, no encontrado y ciudades sin coordenadas | no cubren acentos, ambigüedad, tipos, rate limit ni cache externa |

### Regla de compatibilidad

V1 sigue devolviendo `HotelAreaResolveOut` con sus campos actuales. H12 añade semántica y endpoints/campos de forma aditiva; no cambia `source="internal"` ni `source="nominatim"` existentes.

---

## 3. Vocabulario canónico de destino

### 3.1. Tipos

```text
city
neighborhood
landmark
airport
region
country
postal_area
unknown
```

El tipo lo determina el catálogo/geocoder con evidencia. No inferir `city` solo porque la etiqueta contiene una ciudad.

### 3.2. Resultado de resolución

```json
{
  "destination_id": "opaque-catalog-or-geocoder-id",
  "label": "Madrid",
  "secondary_label": "Comunidad de Madrid, España",
  "type": "city",
  "country_code": "ES",
  "latitude": 40.4168,
  "longitude": -3.7038,
  "bbox": null,
  "confidence": "high",
  "source": "internal_catalog",
  "normalized_query": "madrid",
  "provider_reference": null,
  "is_ambiguous": false,
  "warnings": []
}
```

Campos obligatorios para ejecutar `area_search`:

- `label` visible;
- `type` compatible con el caso de uso;
- `country_code` si está disponible;
- coordenadas válidas o un identificador de área que el adapter pueda consumir;
- `confidence` mínima aprobada;
- `is_ambiguous=false` o una elección explícita del usuario.

`destination_id` y `provider_reference` son opacos. Nunca se usan como `HotelProperty.id`.

### 3.3. Confianza

```text
high
medium
low
unknown
```

Semántica:

- `high`: coincidencia estable, única y suficientemente precisa para el caso de uso.
- `medium`: utilizable con advertencia o confirmación según tipo/mercado.
- `low`: solo sugerencia; no iniciar rates automáticamente.
- `unknown`: no hay evidencia suficiente; no tratar como destino válido.

La confianza no es calidad del provider hotelero, ni freshness, ni probabilidad de disponibilidad. Se conserva separada de H05.

### 3.4. Source

```text
internal_catalog
provider_mapping
geocoder_external
user_selected
legacy_centroid
unknown
```

`legacy_centroid` identifica el resultado actual calculado a partir de hoteles locales, no una entidad geográfica oficial.

---

## 4. Normalización de entrada

La normalización debe ser determinista y no destructiva:

1. recortar espacios y colapsar whitespace;
2. normalizar Unicode y comparar sin acentos para búsqueda;
3. conservar la etiqueta original para copy cuando sea segura;
4. normalizar mayúsculas/minúsculas sin perder idioma;
5. aceptar alias e idiomas conocidos del catálogo;
6. separar códigos de aeropuerto cuando exista patrón válido;
7. limitar longitud y rechazar entradas vacías;
8. no enviar texto arbitrariamente largo al geocoder;
9. no incluir query params privados ni contexto de usuario;
10. registrar solo una versión redacted/normalizada para métricas.

Ejemplos que deben converger en búsqueda interna cuando el catálogo lo permita:

```text
Málaga = Malaga = málaga
Madrid Centro ≠ Madrid ciudad automáticamente
BCN puede ser aeropuerto o código según catálogo
San Sebastián / Donostia puede compartir alias, pero debe conservar etiqueta/country
```

La normalización no debe convertir un barrio en una ciudad sin indicarlo en `type`.

---

## 5. Autocomplete y selección

### 5.1. Contrato de sugerencia

El autocomplete debe devolver una lista limitada y ordenada de `DestinationSuggestion`:

```text
id
label
secondary_label
type
country_code
latitude/longitude o place reference
confidence
source
is_ambiguous
```

Orden recomendado:

1. coincidencia exacta normalizada;
2. alias explícito;
3. tipo compatible con modo seleccionado;
4. país/mercado preferido solo si existe una preferencia explícita;
5. confidence;
6. popularidad/cobertura del catálogo;
7. etiqueta estable como desempate.

No ordenar por un score opaco sin conservar razones internas para observabilidad.

### 5.2. Interacción frontend

- escribir no ejecuta automáticamente una búsqueda de rates;
- seleccionar una sugerencia fija `destination_id/type/source`;
- pulsar buscar con texto ambiguo muestra confirmación o error accionable;
- limpiar el input limpia la resolución elegida;
- cambiar el texto después de seleccionar invalida la selección anterior;
- no permitir que coordenadas antiguas sobrevivan a un nuevo texto;
- teclado y mouse deben producir la misma selección;
- una sugerencia debe mostrar al menos etiqueta, país y tipo cuando haya riesgo de duplicado;
- si el resultado viene de geocoder externo, el copy puede indicar “zona aproximada” sin mostrar códigos internos.

### 5.3. No autocomplete externo indiscriminado

No consultar Nominatim por cada pulsación. El diseño debe aplicar:

```text
debounce
minimum_query_length
local_catalog_first
request cancellation
per-query cooldown
cache TTL
max suggestions
provider budget
```

El número y TTL definitivos se calibran con H17/H37, pero nunca se permite una tormenta de requests por tecla.

---

## 6. Ambigüedad y confirmación

### Casos ambiguos

- mismo nombre en varios países;
- “Madrid Centro” sin definición de radio;
- landmark que no tiene cobertura hotelera propia;
- aeropuerto con ciudad asociada distinta;
- código de aeropuerto que puede ser hotel/ciudad en catálogo;
- geocoder devuelve resultados de tipos incompatibles;
- centroides internos de varias ciudades mezcladas;
- resultado con `confidence=low`.

### Contrato de decisión

| Situación | Resultado | Acción |
|---|---|---|
| única ciudad interna, coordenadas válidas | `resolved/high` | puede continuar |
| varias ciudades posibles | `ambiguous` | pedir país/tipo/selección |
| barrio/landmark válido con coordenadas | `resolved/medium` | continuar mostrando alcance/radio |
| aeropuerto | `resolved/medium` | mostrar tipo y ciudad asociada |
| solo geocoder externo | `resolved/medium` o `low` | confirmar si no hay identidad estable |
| geocoder caído y sin catálogo | `unavailable` | no llamar provider de hoteles |
| query vacía/corta | `invalid_request` | validación inline |
| destino sin hoteles locales pero coordenadas válidas | `resolved` + `no_catalog_coverage` | permitir area search solo si el caso lo permite |

Un resultado `ambiguous` nunca debe elegir silenciosamente el primer país devuelto.

---

## 7. Fallback y geocoder externo

### Orden de resolución

```text
1. catálogo/alias interno
2. mapping provider-neutral si existe y está permitido
3. geocoder externo detrás de adapter
4. fallback explícito/no resuelto
```

El servicio externo no debe convertirse en fuente de verdad del hotel. Solo aporta un punto/área geográfica para continuar con una búsqueda compatible.

### Requisitos del adapter geocoder

- timeout finito;
- user-agent identificable y configurable;
- rate limit local y cooldown;
- cache por query normalizada + idioma/país relevante;
- redaction de URL y respuesta en logs;
- validación de schema y tipo;
- límite de resultados y tamaño de payload;
- cancelación de requests obsoletas;
- métricas de éxito, vacío, timeout, 429, error de parseo y cache hit;
- kill switch `HOTEL_GEOCODER_ENABLED=false`;
- no enviar datos personales;
- no afirmar cobertura hotelera por el mero hecho de geocodificar.

La llamada actual a Nominatim y su `sleep(1.0)` son una implementación V1 observable, no un contrato suficiente para autocomplete de producción.

### Cache

La cache de destino puede compartir resultados anónimos. La clave debe incluir:

```text
normalized_query
language/locale si cambia etiqueta
country_hint si se proporciona explícitamente
resolver_version
```

Nunca incluir `user_id`, email, token ni coordenadas privadas en una clave compartida.

---

## 8. API V1 y evolución aditiva

### V1 conservada

`GET /api/v1/hotels/area-resolve?q=...` sigue devolviendo:

```json
{
  "area_label": "Madrid",
  "latitude": 40.4168,
  "longitude": -3.7038,
  "country_code": "ES",
  "confidence": "high",
  "source": "internal"
}
```

V1 no debe fingir que `area_label` identifica un tipo geográfico ni que `confidence` tiene la semántica completa H12.

### Contrato aditivo propuesto

Sin romper V1, añadir internamente/externamente campos opcionales o un endpoint de sugerencias:

```json
{
  "data": {
    "selection": {
      "destination_id": "opaque-id",
      "label": "Madrid",
      "secondary_label": "España",
      "type": "city",
      "country_code": "ES",
      "latitude": 40.4168,
      "longitude": -3.7038,
      "confidence": "high",
      "source": "internal_catalog",
      "is_ambiguous": false
    },
    "suggestions": [],
    "warnings": []
  },
  "meta": {
    "resolver_version": "h12-1",
    "cache_hit": true
  }
}
```

Los envelopes generales de resultados y paginación se definen en H15, no se duplican aquí.

### Decisiones deliberadamente diferidas

H12 no congela todavía el nombre final de la ruta de autocomplete ni su envelope público. H13/H17 deben decidir y probar, antes de conectar el frontend:

- ruta/versionado exactos para sugerencias;
- schema OpenAPI/TypeScript único de `DestinationSuggestion`;
- `limit`, debounce, cancelación y códigos HTTP;
- política de cache y `resolver_version`;
- compatibilidad con el `/area-resolve` V1 existente.

El uso de Nominatim/geocoder externo requiere además revisión H35 de atribución, términos de uso, user-agent, límites, retención y cualquier obligación de mostrar fuente. La existencia de `NOMINATIM_URL` en la configuración local no constituye aprobación legal ni operativa.

### Errores mínimos

```text
invalid_destination_query
ambiguous_destination
destination_not_found
destination_geocoder_unavailable
destination_provider_rate_limited
destination_invalid_response
destination_low_confidence
```

El backend devuelve códigos estables; el frontend resuelve copy i18n. No enviar mensajes crudos del geocoder.

---

## 9. Frontend y estados de UI

El estado mínimo de resolución es:

```text
idle
searching
suggestions
selected
ambiguous
unavailable
invalid
```

Reglas:

- `idle`: sin query o query no iniciada;
- `searching`: hay request activa, cancelar la anterior si cambia el texto;
- `suggestions`: hay candidatos seleccionables;
- `selected`: selección válida conservada;
- `ambiguous`: no iniciar area search hasta confirmar;
- `unavailable`: mostrar retry/fallback interno;
- `invalid`: feedback inline y foco en el input.

El frontend no debe usar `results.length === 0` para distinguir destino no encontrado, provider error o zona sin hoteles. Esa distinción depende del contrato de H15/ProviderResult.

### Accesibilidad

- lista con roles semánticos y navegación de teclado;
- opción activa anunciada;
- país/tipo accesibles para lector de pantalla;
- no depender solo de color para `confidence`;
- estado de carga y error anunciado;
- selección visible y removible;
- touch target mínimo conforme a contrato frontend del repositorio.

---

## 10. Tests y métricas

### Backend unitarios

- acentos, casefold y alias;
- query vacía/larga/inválida;
- ciudad única y varias ciudades homónimas;
- tipo city/neighborhood/landmark/airport/region;
- país y etiquetas consistentes;
- geocoder timeout/429/JSON inválido;
- cache hit evita request;
- flag off no llama geocoder;
- no se filtran user/token/URL completa;
- fallback interno conserva `source` correcto;
- coordenadas inválidas se rechazan;
- confidence no se confunde con freshness.

### Integración

- `/area-resolve` V1 sigue serializando;
- autocomplete/sugerencias devuelve candidatos deterministas;
- selección ambigua bloquea area search;
- geocoder externo caído deja error accionable;
- cambiar query invalida coordenadas anteriores;
- zona sin hoteles distingue resolución válida de resultados vacíos;
- SQLite/test fixtures y adapter mock no hacen requests externos.

### Frontend

- teclado/mouse seleccionan la misma sugerencia;
- limpiar input elimina selección;
- país/tipo aparecen en duplicados;
- errores i18n estables;
- no se dispara búsqueda con selección ambigua;
- no se conserva stale `areaResolved` tras editar texto;
- tests de accesibilidad y responsive del panel.

### Métricas

```text
destination_resolution_requests_total{source,outcome}
destination_resolution_cache_hits_total
destination_resolution_ambiguous_total
destination_resolution_low_confidence_total
destination_geocoder_requests_total{outcome}
destination_geocoder_rate_limited_total
destination_geocoder_latency_ms
destination_search_blocked_ambiguous_total
destination_search_no_catalog_coverage_total
```

---

## 11. Handoff y gate

| Fase | Entrega H12 |
|---|---|
| H13 | selección estable para formulario, URL state, submit y restauración |
| H14 | filtros/orden aplicados a una resolución con tipo/radio explícitos |
| H15 | envelope de resultados, warnings, errores y paginación; distinguir vacío de unavailable |
| H17 | autocomplete real, catálogo/alias y mercados prioritarios |
| H35 | privacidad, límites del geocoder, user-agent, retención y redaction |
| H37 | cache, latencia, coste operativo y límites de geocoder |
| H41 | métricas de source, confidence, ambigüedad y fallback |

H12 podrá considerarse implementada cuando:

- entradas con acentos/alias resuelvan consistentemente;
- resultados incluyan tipo, país, source y confidence;
- consultas ambiguas pidan confirmación;
- geocoder externo esté aislado, limitado, cacheado y apagable;
- no haya requests por tecla sin debounce/cancelación;
- fallback interno/external tenga estados visibles y no filtre datos;
- frontend no confunda lista vacía con error;
- tests cubran V1, sugerencias, ambigüedad, error y accesibilidad.

**Resultado H12:** contrato de destino aprobado. La implementación actual sigue siendo V1 —resolución interna más fallback Nominatim— y no se presenta todavía como autocomplete de producción completo.
