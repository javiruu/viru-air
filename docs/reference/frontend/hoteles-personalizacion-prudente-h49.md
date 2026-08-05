# H49 — Personalización hotelera prudente y explicable

**Estado:** COMPLETA como contrato de producto/ranking; aplicación al ranking hotelero, perfil hotelero, controles, migración y QA pendientes  
**Fecha:** 2026-08-05  
**Área:** producto / frontend / backend / ranking / privacidad / i18n / QA  
**Fuente de verdad:** sí para la semántica de personalización hotelera opcional y explicable  
**Fase del roadmap:** H49  
**Depende de:** [H17 — ranking explicable](../backend/hoteles-ranking-explainability-h17.md), [H34 — i18n, fechas y monedas](hoteles-localization-dates-currency-timezones-h34.md), [H38 — ownership, secretos y abuso](../backend/hoteles-ownership-secrets-ssrf-abuse-h38.md), [H47 — Mis hoteles](hoteles-mis-hoteles-reengagement-h47.md), [H48 — búsquedas guardadas/compartibles](../backend/hoteles-busquedas-guardadas-compartibles-h48.md)  
**Handoff:** [H50 — afiliación, atribución y costes](../../plans/2026-08-04-hoteles-master-roadmap.md#fase-h50--monetización-y-afiliación-responsable)

> H49 no intenta adivinar a la persona ni sustituir su criterio. Permite que Viru recuerde preferencias hoteleras que la persona ha declarado, explique cuándo influyen y ofrezca volver en cualquier momento a un orden neutral.

## 1. Decisión de producto

H49 define una personalización **prudente** con cinco propiedades obligatorias:

1. **Opcional:** la experiencia útil no depende de aceptar personalización.
2. **Explícita:** una preferencia declarada tiene precedencia sobre una inferencia.
3. **Explicable:** cada cambio de orden comunica qué preferencia y qué evidencia lo provocaron.
4. **Reversible:** la persona puede desactivar, ajustar, resetear y borrar el perfil aplicado.
5. **Acotada:** solo puede afectar a `recommended`; nunca modifica silenciosamente `price`, `distance` o `stars`.

La personalización no convierte una señal en garantía de precio, disponibilidad, calidad del hotel o conveniencia universal. Tampoco sustituye filtros explícitos: si la persona excluye una condición, el filtro sigue siendo una restricción, no un peso blando.

### 1.1. No objetivos

H49 no implementa por sí sola:

- un modelo de machine learning, perfil demográfico o sistema de publicidad;
- inferencias sobre salud, discapacidad, religión, etnia, género, orientación, ingresos u otros atributos sensibles;
- personalización del ranking objetivo por comisión, afiliación, partner o margen;
- tracking, alertas, delivery, reserva o conversión de una búsqueda;
- una nueva plataforma de identidad o un nuevo servicio externo;
- una promesa de que el resultado personalizado es “el mejor hotel”;
- un score visible que pretenda ser confianza, probabilidad de reserva o satisfacción;
- una llamada provider adicional solo para calcular una preferencia;
- persistencia de datos privados en una URL compartible de H48.

## 2. Baseline real comprobable

### 2.1. Preferencias existentes

`backend/app/api/v1/preferences.py` y el modelo de preferencias actual permiten guardar principalmente preferencias de búsqueda de vuelos/región y presentación:

- radio por defecto;
- escalas y aeropuertos cercanos;
- guías de precio/calendario;
- ventanas horarias;
- filtros estrictos;
- moneda preferida, idioma y quiet hours;
- tema, densidad, reduced motion y alto contraste en el bloque de apariencia.

`frontend/src/modules/preferences/searchPreferences.ts` valida y resume preferencias de Quick Search. No demuestra un perfil hotelero separado ni un contrato de pesos hoteleros. `preferred_currency`, locale, tema y quiet hours pueden reutilizarse como contexto, pero no deben interpretarse automáticamente como preferencias de ranking hotelero.

### 2.2. Ranking y explicadores existentes

H17 define el contrato hotelero de `price`, `distance`, `stars` y el futuro `recommended`, pero deja explícito que:

- la implementación hotelera V2 y sus metadata están pendientes;
- no existe todavía un `recommended` hotelero habilitado;
- el frontend no debe reordenar ni fabricar scores;
- `has_tracking` no puede ser bonus de ranking;
- paridad, freshness y provider son señales separadas.

Existen explicadores y pesos en `frontend/src/modules/recommendations/`, así como ranking de Quick Search en `backend/app/services/quick_search_ranking.py`. Son patrones de otros dominios, no una personalización hotelera ya activa. No se copian sus claves, pesos o scores como si fueran contrato de `/hoteles`.

### 2.3. Historial, tracking y señales

Watchlist, tracked offers, histórico, alertas e inbox son superficies de retención y contexto. Su existencia no autoriza a inferir automáticamente gustos ni a reordenar hoteles:

- un favorito expresa interés por una propiedad, no necesariamente preferencia general;
- un tracking expresa una estancia/oferta concreta, no una orden universal por precio;
- abrir una notificación es una acción de retorno, no consentimiento para perfilar;
- un click, dwell time o apertura puede ser una señal de producto, pero no se convierte en preferencia persistida sin política explícita.

## 3. Modelo de preferencias

### 3.1. Tres clases separadas

| Clase | Ejemplo | Puede alterar `recommended` | Retención/ownership |
|---|---|---:|---|
| **Declarada** | “priorizar cancelación flexible” o “prefiero 4+ estrellas” | sí, tras consentimiento/activación | cuenta del usuario, editable y borrable |
| **Contextual de sesión** | moneda, fechas, destino, filtro elegido en esta búsqueda | solo durante la sesión/query | no se convierte en perfil por defecto |
| **Inferida** | patrón de clicks o aperturas repetidas | no por defecto; solo tras política/opt-in explícito | separada, explicable, con reset y retención limitada |

Las preferencias declaradas siempre tienen prioridad. Una inferencia no puede contradecir un filtro, una exclusión, una selección de fechas ni una preferencia declarada sin pedir confirmación.

### 3.2. Preferencias hoteleras iniciales permitidas

La primera versión puede contemplar únicamente dimensiones observables y no sensibles, cuando H10/H15/H19 las respalden:

- rango de precio o sensibilidad al presupuesto, sin convertirlo en dato de ingresos;
- distancia/radio respecto al destino;
- categoría/estrellas;
- cancelación flexible o no reembolsable;
- régimen/comidas cuando esté normalizado;
- tipo de alojamiento o amenities allowlisted;
- moneda y región de presentación;
- prioridad entre precio, distancia, categoría y condiciones comparables;
- preferencia de recibir o silenciar señales hoteleras, separada de la ordenación.

No se guarda una preferencia si la dimensión no está respaldada por el contrato de datos. “Me gustan hoteles tranquilos”, por ejemplo, no puede convertirse en señal de ranking hasta que exista un campo hotelero verificable y una política clara de evidencia.

### 3.3. Modelo objetivo

El perfil hotelero futuro debe ser explícito y versionado. No se exige adoptar este nombre exacto, pero cualquier implementación debe conservar sus fronteras:

```text
HotelPersonalizationProfile {
  id: opaque-private-id
  user_id: owner-only
  schema_version
  mode: off | declared_only | declared_plus_inferred
  declared_preferences: allowlisted values
  inferred_preferences: allowlisted values, nullable
  source_summary: declared | session | inferred
  ranking_policy_version
  created_at
  updated_at
  last_used_at nullable
  expires_at nullable
}
```

Requisitos:

- `id` y `user_id` son privados y no aparecen en URLs públicas, clipboard, deeplinks o labels visibles;
- `declared_preferences` y `inferred_preferences` no se mezclan en un blob opaco;
- cada dimensión incluye fuente, fecha, confianza de evidencia y versión de política si se persiste;
- los datos inferidos tienen TTL/retención independiente y se pueden borrar sin borrar búsquedas guardadas H48;
- no se guarda raw clickstream, texto libre innecesario ni payload de provider como sustituto del perfil;
- un usuario anónimo recibe baseline neutral o preferencias temporales de sesión, no perfil persistente oculto.

## 4. Ranking y reglas de aplicación

### 4.1. Órdenes objetivos intactos

Estos órdenes deben producir el mismo resultado con los mismos datos, query y versión, independientemente del usuario:

```text
price
 distance
stars
```

No pueden alterarlos:

- favoritos o tracking existentes;
- aperturas del inbox;
- historial privado;
- comisión o partner;
- perfil inferido;
- país, idioma o tema, salvo formato de presentación;
- ausencia de consentimiento para personalización.

### 4.2. `recommended` como único punto personalizable

`recommended` solo puede activarse cuando H17 haya cerrado:

- features y fuentes comparables;
- fórmula y pesos versionados;
- metadata de ranking;
- políticas de missing data, stale, provider parcial y afiliación;
- explanation por resultado;
- flag, canary y rollback.

La personalización puede ajustar pesos dentro de límites aprobados, pero nunca inventar una feature ausente ni convertir un resultado no elegible en recomendado. Si el contexto o las capacidades no permiten explicar el orden, se hace fallback a orden estricto y se comunica la razón.

### 4.3. Precedencia normativa

La resolución de una query sigue este orden:

1. filtros y exclusiones explícitas de la búsqueda;
2. condiciones de estancia y comparabilidad H10/H19;
3. restricciones de disponibilidad/procedencia/freshness H05/H25;
4. orden elegido por la persona (`price`, `distance`, `stars`);
5. `recommended` solo si se eligió/activó y existe capability;
6. preferencias declaradas permitidas;
7. inferencias permitidas, solo en modo explícito y dentro de límites;
8. desempates deterministas H17.

Una preferencia nunca puede hacer aparecer un resultado que incumple un filtro ni ocultar de forma absoluta una categoría elegible sin una razón visible y un control de recuperación.

### 4.4. Explicación mínima

La respuesta futura debe transportar códigos allowlisted, no una frase inventada por cada cliente:

```json
{
  "personalization": {
    "mode": "declared_only",
    "profile_version": "hotel_personalization.v1",
    "applied": true,
    "reasons": [
      {
        "code": "flexible_cancellation_preference",
        "source": "declared",
        "weight_direction": "up",
        "evidence": {"cancellation": "free_until_2026-09-08"}
      }
    ],
    "fallback": null
  }
}
```

La UI puede traducir el código a copy ES/EN como “Sube porque priorizas cancelación flexible”. Debe permitir abrir “por qué” y ver la evidencia resumida. No debe mostrar pesos internos, user IDs, raw provider ni un “match score” sin definición.

Si no hay personalización aplicada, el estado explícito es `off`, `not_available`, `not_eligible` o `fallback_strict`; no se muestra una etiqueta vacía de “para ti”.

## 5. Cold start, controles y reversibilidad

### 5.1. Primera visita y usuarios anónimos

- mostrar orden neutral y contexto de búsqueda;
- no bloquear con un modal de preferencias;
- ofrecer controles opcionales después de que exista una query válida;
- no recolectar historial de navegación hotelera para perfilar sin base legal/consentimiento aprobado;
- rotular demo, cache, stale y provider parcial según H05/H25;
- no penalizar a una persona por no activar personalización.

### 5.2. Controles visibles

La superficie “Ajustar resultados” debe ofrecer, como mínimo:

- activar/desactivar personalización;
- elegir dimensiones declaradas allowlisted;
- ver qué preferencias están activas y su fuente;
- cambiar de `recommended` a `price`, `distance` o `stars`;
- abrir explicación por resultado;
- resetear preferencias inferidas;
- borrar el perfil hotelero persistido;
- conservar la búsqueda H48 sin convertirla en perfil.

“Desactivar” debe tener efecto inmediato para nuevas respuestas y no requiere borrar favoritos, tracking, alertas o búsquedas guardadas.

### 5.3. Reset y borrado

`reset` elimina pesos inferidos y vuelve al baseline neutral. `delete` elimina el perfil hotelero y sus caches derivadas según H35/H38, pero no borra automáticamente recursos independientes del usuario. La respuesta debe ser idempotente y no revelar si existía un perfil en otra cuenta.

Logout, expiración de sesión, cambio de cuenta y cambio de locale deben invalidar el contexto privado de personalización; no se puede reutilizar una cache de ranking de A para B.

## 6. Privacidad, fairness y seguridad

### 6.1. Minimización y ownership

- autorización server-side por `user_id` autenticado;
- ningún `profile_id`, `user_id`, inferencia o label privado en H48 share URLs;
- cache pública solo con ranking neutral y fingerprint de query no privada;
- cache personalizada particionada por usuario, versión y policy, o `no-store`;
- analytics con códigos agregados y fingerprint opaca, sin URL completa, email, IP innecesaria, raw clickstream o atributos sensibles;
- exportación y borrado del perfil incluidos en la política de cuenta;
- respuestas de perfil inexistente/no autorizado genéricas cuando exista riesgo de enumeración.

### 6.2. Atributos prohibidos

No se infieren, almacenan ni usan para ranking atributos sensibles o proxies obvios de ellos. Tampoco se usa precio para deducir ingresos ni país/idioma como proxy de capacidad económica. La moneda elegida solo formatea o convierte según H34; no modifica la utilidad del ranking.

### 6.3. Límites de diversidad y neutralidad

Personalización no puede suprimir completamente inventario elegible por una dimensión blanda. La implementación debe definir:

- límites máximos de peso y desplazamiento;
- exposición de alternativas neutrales;
- fallback si faltan datos;
- fixtures con perfiles opuestos y cold start;
- revisión de resultados por segmentos de datos, no por atributos personales sensibles;
- kill switch para desactivar la política sin migrar perfiles.

No se presenta un control de fairness como certificación matemática; es un conjunto de guardrails verificables y revisables.

## 7. Freshness, providers, demo y estados

La personalización no rescata datos inválidos:

| Estado del dato | Tratamiento personalizado |
|---|---|
| `fresh`/`recent` y comparable | puede participar si la feature está permitida |
| `stale`/`expired` | no recibe bonus de frescura; muestra limitación y puede caer a estricto |
| `partial`/`unknown` | no se inventa evidencia; explanation lo refleja |
| provider error/429/timeout | no se convierte en preferencia negativa ni `sold_out`; conserva contexto |
| `fixture_demo` | nunca se usa como evidencia de gusto o disponibilidad real |
| `recommended` no elegible | fallback a `price`/orden elegido, con razón |

Cambiar provider, schema o `ranking_policy_version` invalida caches personalizadas incompatibles. Abrir o guardar una búsqueda H48 no ejecuta provider ni genera perfil implícito.

## 8. i18n, accesibilidad y UX

- todos los códigos de razón tienen ES/EN y parámetros localizables;
- el copy distingue “preferencia declarada”, “basado en esta búsqueda” e “inferencia”, sin presentar una inferencia como hecho personal;
- el control de personalización tiene label, estado, ayuda y error accesibles;
- “Por qué aparece aquí” expone razón y evidencia resumida mediante `aria-describedby`/dialog accesible;
- el foco vuelve al control que abrió el detalle;
- los estados `off`, `applying`, `applied`, `fallback_strict`, `error` y `reset_success` se anuncian sin depender de color o toast;
- teclado, zoom 200%, móvil, dark/light y reduced motion cumplen H32-H34/H40;
- el cambio de orden conserva fechas, destino, filtros, query fingerprint y selección válida;
- no se muestran IDs de perfil, pesos secretos, tokens ni campos privados en DOM, clipboard o aria-labels.

## 9. Instrumentación y observabilidad

Eventos allowlisted:

```text
hotel_personalization_viewed
hotel_personalization_enabled
hotel_personalization_disabled
hotel_personalization_preference_declared
hotel_personalization_preference_updated
hotel_personalization_inference_applied
hotel_personalization_explanation_shown
hotel_personalization_explanation_dismissed
hotel_personalization_reset
hotel_personalization_profile_deleted
hotel_personalization_fallback_strict
hotel_personalization_missing_feature
hotel_personalization_policy_blocked
```

Propiedades permitidas: `policy_version`, `profile_mode`, `source=declared|session|inferred`, `dimension_allowlisted`, `sort_requested`, `sort_applied`, `outcome`, `reason_code`, locale, theme, viewport y bucket agregado. No registrar perfil completo, query completa, user ID crudo, hotel history raw, email, atributos sensibles ni peso privado sin necesidad aprobada.

Dashboards deben separar:

- órdenes estrictos frente a `recommended`;
- personalización activa frente a fallback;
- cold start frente a perfil existente;
- stale/provider/demo;
- explicación mostrada frente a ausencia de explicación;
- opt-out/reset y errores de ownership.

La interacción con una recomendación no prueba que el orden fuera correcto. Es una señal de utilidad/confianza que debe revisarse junto a guardrails.

## 10. Tests y gates de aceptación

### Unit/contract

- `price`, `distance` y `stars` son idénticos entre usuarios con misma query/datos/versión;
- favorito, tracking, inbox y apertura de detalle no alteran orden objetivo;
- filtros explícitos vencen a cualquier preferencia;
- preferencia declarada vence a inferencia contradictoria;
- usuario anónimo obtiene baseline neutral;
- `recommended` queda bloqueado sin capability, feature o explicación;
- explicación coincide con features realmente aplicadas;
- missing/stale/partial/demo no recibe bonus accidental;
- pesos y desplazamientos respetan límites versionados;
- reset vuelve al orden neutral y delete es idempotente;
- usuario B no puede leer, modificar, borrar ni inferir el perfil de A;
- cache personalizada no cruza usuarios, locale, query fingerprint o policy version;
- H48 share URL no contiene profile/user/inference fields;
- no hay provider call ni perfil persistido implícito al abrir/guardar una búsqueda;
- telemetry redacts private and sensitive fields.

### Integration/browser

1. abrir `/hoteles` sin perfil y comprobar cold start neutral;
2. elegir una preferencia declarada permitida;
3. activar `recommended` y verificar explanation respaldada;
4. cambiar a `price` y comprobar que el orden objetivo no depende del perfil;
5. desactivar y resetear; verificar fallback inmediato;
6. abrir una URL H48 en otra sesión y comprobar que no arrastra personalización;
7. intentar acceso cruzado con dos usuarios y comprobar respuesta genérica;
8. simular stale, provider off, partial y demo; comprobar copy y acciones honestas;
9. cambiar ES/EN, dark/light, móvil, teclado, zoom y reduced motion;
10. repetir con respuesta tardía y back/forward sin reordenación stale.

### Gate H49

H49 podrá considerarse implementada cuando:

1. los órdenes objetivos permanecen deterministas y no personalizados;
2. `recommended` tiene capability, fórmula, versión y explicación respaldada;
3. preferencias declaradas, contextuales e inferidas están separadas;
4. cold start funciona sin perfil oculto ni prompt bloqueante;
5. existen controles de activar, ajustar, explicar, desactivar, resetear y borrar;
6. no se usan atributos sensibles, comisión ni tracking como bonus oculto;
7. privacidad, ownership, cache y exportación/borrado están cubiertos;
8. stale, provider error, partial y demo degradan con honestidad;
9. ES/EN, a11y, responsive, reduced motion y browser QA pasan;
10. tests cross-user, flags, fallback y telemetría redacted pasan;
11. H48 conserva la separación entre query compartible y perfil privado;
12. H50 puede definir afiliación sin esconder `affiliate_bonus` en el ranking.

**Resultado contractual:** H49 queda definida como personalización hotelera opcional, explícita, acotada a `recommended`, explicable y reversible. El repositorio tiene preferencias y explicadores de otros dominios, además del contrato H17 de ranking hotelero, pero todavía no demuestra un perfil hotelero, `recommended` personalizado, controles de reset/borrado ni integración de ranking; implementación y QA permanecen pendientes.
