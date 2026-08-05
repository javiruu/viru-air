# H01 — Visión de producto de `/hoteles`

**Estado:** vivo — definición de producto para ejecución  
**Fecha:** 2026-08-04  
**Área:** producto / hoteles  
**Fuente de verdad:** sí para la dirección de producto; los contratos técnicos siguen en `docs/specs/` y en el código.

## 1. La promesa de producto

`/hoteles` será el lugar al que una persona vuelve cuando quiere **encontrar una estancia con buen precio, entender si ese precio merece confianza y no perderse una bajada**.

Viru no tiene que ganar por tener más paneles. Tiene que ganar por quitar incertidumbre:

- “¿Estoy comparando la misma estancia?”
- “¿Este precio es de verdad comparable?”
- “¿Ha cambiado desde ayer?”
- “¿Me conviene reservar o esperar?”
- “¿Me avisará Viru si merece la pena volver?”

La experiencia debe sentirse cercana y cuidada: suficientemente potente para quien compara en serio, pero nunca como una consola B2B de revenue management.

## 2. Usuario principal y momento de uso

### Usuario principal

Persona que organiza un viaje y está buscando alojamiento para unas fechas concretas. Puede saber el hotel exacto o estar abierta a varias opciones de una zona. Quiere ahorrar tiempo y dinero, pero no quiere aprender jerga de proveedores ni interpretar datos dudosos.

### Momentos de uso prioritarios

1. **Explorar:** “Quiero ir a Madrid un fin de semana; ¿qué opciones tienen sentido?”
2. **Comparar:** “Estos tres hoteles parecen parecidos; ¿cuál tiene el precio y condiciones más claras?”
3. **Vigilar:** “Me gusta este hotel, pero todavía no quiero reservar; avísame si baja.”
4. **Decidir:** “Ha bajado, el dato es reciente y la cancelación me encaja; ahora sí quiero abrir el partner.”
5. **Volver:** “Recibí una alerta; quiero ver qué cambió y decidir rápido.”

## 3. Personas de trabajo

Estas personas son herramientas de priorización, no perfiles rígidos ni datos sensibles.

### P1 — Escapada urbana con poco tiempo

- Busca ciudad/zona, fechas y una habitación.
- Quiere resultados rápidos, lectura sencilla y pocos filtros importantes.
- Le importan precio total, ubicación, cancelación y poder guardar una opción.
- Tolera poca complejidad; abandona si el primer paso parece técnico.

**Necesidad:** primera búsqueda y primer guardado sin explicación externa.

### P2 — Viajero sensible al precio

- Compara varias opciones y vuelve varias veces.
- Quiere mínimo histórico, cambios recientes y alertas configurables.
- Valora saber si el precio es comparable y cuándo se comprobó.
- Está dispuesto a activar seguimiento si entiende qué se vigila.

**Necesidad:** confianza en el histórico y alertas sin ruido.

### P3 — Viaje familiar o de grupo

- Usa más de una habitación, varios adultos y posiblemente niños.
- Necesita que la ocupación quede visible y no se compare una tarifa incompatible.
- Da mucha importancia a cancelación, régimen y precio total.

**Necesidad:** formulario y resultado que no escondan la composición de la estancia.

### P4 — Usuario con hotel elegido

- Ya conoce la propiedad y quiere vigilar una estancia concreta.
- Necesita introducir fechas, ocupación y condiciones exactas.
- No quiere que “guardar hotel” se confunda con “seguir precio”.

**Necesidad:** crear un tracking completo desde una oferta entendible.

### P5 — Usuario flexible y recurrente

- Puede cambiar fechas, zona o categoría.
- Vuelve con frecuencia para explorar oportunidades.
- Es candidato a búsquedas guardadas, calendario flexible y personalización prudente.

**Necesidad:** retorno rápido sin sacrificar transparencia.

## 4. Jobs-to-be-done y criterios de éxito

| Job | Cuando… | Quiero… | Para… | Evidencia de que funciona |
|---|---|---|---|---|
| Encontrar | tengo destino y fechas | buscar sin fricción | llegar a opciones útiles | búsqueda completada sin error |
| Entender | veo un resultado | saber precio, condiciones y freshness | comparar sin engañarme | detalle/card comprensible |
| Filtrar | hay muchas opciones | reducir resultados con criterios reales | no perder tiempo | filtros aplicados y reversibles |
| Guardar | me gusta un hotel | conservarlo | volver luego | favorito visible al regresar |
| Vigilar | aún no quiero reservar | seguir una estancia concreta | capturar una bajada | tracking con snapshot inicial |
| Confiar | recibo un cambio | saber qué cambió y con qué evidencia | decidir | alerta trazable a snapshots |
| Actuar | el precio merece la pena | abrir el partner correcto | reservar fuera de Viru | deeplink seguro y contexto visible |
| Volver | el viaje sigue pendiente | retomar rápido | no repetir trabajo | deep link/inbox conserva contexto |

## 5. Flujo principal comprometido

```text
1. Entrar en /hoteles
2. Entender la promesa en una frase
3. Introducir destino
4. Elegir fechas y ocupación
5. Buscar
6. Ver resultados con precio y condiciones comparables
7. Abrir detalle o seleccionar una oferta
8. Guardar o seguir precio
9. Ver confirmación de qué se vigilará
10. Recibir cambio en inbox/canal aceptado
11. Volver al tracking, entender el delta y abrir partner
```

### Reglas de la experiencia

- El buscador es protagonista.
- Una card no debe tener dos acciones primarias compitiendo.
- “Guardar” y “seguir precio” tienen nombres y consecuencias distintas.
- El precio siempre lleva contexto de estancia, moneda y fecha de comprobación.
- Si no hay evidencia suficiente, la experiencia lo explica y ofrece una alternativa.
- La inteligencia secundaria aparece cuando ayuda a decidir, no antes.

## 6. No-objetivos explícitos

En este programa no se pretende:

1. Ser una OTA ni gestionar reservas, pagos, cancelaciones o soporte de booking.
2. Construir un producto B2B de revenue management.
3. Convertir comp sets/paridad en la pantalla principal.
4. Prometer cobertura mundial desde el primer día.
5. Llamar “live” a datos cacheados o históricos.
6. Integrar proveedores externos sin cuotas, coste, términos y plan de salida.
7. Añadir reviews, mapas avanzados, IA conversacional o calendario flexible antes de resolver el flujo exacto.
8. Optimizar afiliación a costa de precio comparable, transparencia o accesibilidad.
9. Eliminar sin migración la watchlist simple o los históricos existentes.
10. Confundir un prototipo con una garantía de disponibilidad hotelera.

## 7. Pilares de valor

### A. Comparación que se entiende

Misma estancia, precio comparable, condiciones visibles y ranking explicable.

### B. Seguimiento que cumple

La persona sabe qué se vigila, cuándo se comprobó y qué ocurrirá si cambia.

### C. Confianza honesta

Provider, freshness, limitaciones, fees y partner se comunican sin prometer más de lo que sabemos.

### D. Regreso útil

Una alerta o visita posterior lleva a una decisión, no a una bandeja de ruido.

### E. Calidez Viru

La interfaz debe sentirse diseñada, humana y viva. No será un dashboard gris ni una copia de un comparador genérico.

## 8. Métricas de producto

### Embudo principal

1. `hotel_page_viewed`
2. `hotel_search_started`
3. `hotel_search_completed`
4. `hotel_result_opened`
5. `hotel_favorite_created`
6. `hotel_tracking_created`
7. `hotel_alert_created`
8. `hotel_alert_opened`
9. `hotel_partner_clicked`

### Métricas objetivo de aprendizaje

No fijamos números arbitrarios antes del baseline; H04 debe convertirlas en objetivos por cohorte. Las métricas mínimas son:

- tasa de búsqueda completada;
- tiempo hasta primer resultado útil;
- porcentaje de resultados con precio/condiciones suficientes;
- resultado → detalle;
- resultado/detalle → favorito;
- resultado/detalle → tracking;
- tracking que recibe al menos una comprobación válida;
- alertas con cambio real frente a alertas suprimidas por dedupe;
- retorno tras alerta;
- seguimiento activo a 7 y 30 días;
- error/partial/stale rate por provider;
- click a partner;
- feedback de precio o condiciones incorrectas;
- coste por búsqueda y por tracking activo.

### Guardrails no negociables

Ninguna mejora de conversión se acepta si empeora materialmente:

- falsos estados live;
- alertas repetidas o irrelevantes;
- falta de transparencia de fees/partner;
- accesibilidad;
- ownership/privacidad;
- coste operativo sin límite.

## 9. Eventos y privacidad

Los eventos deben registrar intención y resultado, no payloads innecesarios.

### Permitido por defecto

- tipo de acción;
- estado de éxito/error/partial;
- cantidad de resultados;
- filtros abstractos o categorías;
- provider lógico y código de warning;
- duración y freshness bucket;
- tracking/resultado IDs internos no reversibles públicamente.

### Evitar por defecto

- email, nombre, token o secretos;
- dirección precisa si no es necesaria;
- payload crudo de provider;
- fechas/ocupación en sistemas analíticos externos si no hay base legal y necesidad clara;
- URLs completas con parámetros sensibles.

## 10. Decisiones para H03

H03 debe convertir esta visión en wireflows y estado de navegación, respetando:

- búsqueda principal arriba;
- resultados con filtros y orden;
- detalle que conserve la búsqueda;
- tracking accesible sin abrir un panel técnico interminable;
- inbox/deeplink de vuelta a una estancia concreta;
- mobile como flujo primario, no una adaptación tardía.

## 11. Gate de H01

**Aprobado como definición de dirección.** H01 queda completo cuando las siguientes preguntas tienen respuesta en este documento:

- ¿A quién sirve `/hoteles`? Sí.
- ¿Qué problema prioritario resuelve? Encontrar, comparar y vigilar una estancia con confianza. Sí.
- ¿Qué no construimos? Sí.
- ¿Cómo sabemos que mejora? Embudo, métricas de utilidad, confianza y guardrails. Sí.
- ¿Qué debe evitar la siguiente IA? Copiar paneles, sobreprometer live, mezclar favorito/tracking y optimizar solo clicks. Sí.

## 12. Handoff

- H02 debe contrastar esta visión con patrones observables y señalar qué encaja/no encaja.
- H03 debe producir arquitectura de información y navegación, no una implementación todavía.
- H05/H06 deben convertir “confianza” y “qué se vigila” en contratos verificables.
- H07/H08 deben comprobar si los providers pueden sostener esta promesa en mercados concretos.
