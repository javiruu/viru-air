# H02 — Benchmark de Travel Price Drops Hotels y traducción a Viru

**Estado:** completo como benchmark fechado; revisar cuando se tomen decisiones que dependan de capacidades externas  
**Fecha de observación:** 2026-08-04  
**Área:** producto / benchmark / hoteles  
**Referencia:** https://travelpricedrops.com/hotels?lng=es  
**Regla:** usar patrones observables como inspiración; no copiar marca, copy, diseño, contenido ni implementación.

## 1. Resumen

Travel Price Drops presenta hoteles como una experiencia de meta-búsqueda orientada a comparar y redirigir, con una propuesta muy directa: destino, fechas, ocupación, resultados y aviso cuando el precio baje. La fuerza de la referencia no está en tener muchos paneles técnicos, sino en hacer visible pronto el valor de volver a buscar y vigilar precios.

Para Viru, la lección principal es:

> `/hoteles` debe explicar el beneficio de seguir una estancia dentro del propio flujo de búsqueda, pero solo prometer el grado de frescura y disponibilidad que nuestros providers realmente pueden sostener.

## 2. Hechos observados en la referencia

### 2.1. Navegación e IA

- Existe una navegación global por verticales de viaje: vuelos, hoteles, coches y cruceros.
- La vertical de hoteles tiene una ruta propia `/hotels`.
- `?lng=es` cambia la localización visible al español.
- La experiencia se comporta como un intermediario/meta-buscador, no como el vendedor final de la reserva.

### 2.2. Formulario

Se observan como elementos principales:

- destino, con copy tipo “Voy a”;
- entrada;
- salida;
- selector agrupado de habitaciones/personas;
- CTA de búsqueda;
- una propuesta de aviso de bajada de precios cercana al flujo principal.

La ocupación inicial parece simplificada para no bloquear la primera búsqueda; esto no demuestra que todos los casos avanzados estén soportados en la misma superficie.

### 2.3. Tracking/alertas

- La acción de recibir avisos de bajada está visible y se formula en lenguaje de beneficio: “Avisarme cuando bajen los precios”.
- El patrón conecta una búsqueda concreta con un retorno posterior.
- La referencia hace que el seguimiento sea parte del producto principal, no una función escondida en ajustes.

### 2.4. Precio, partners y confianza

- La plataforma redirige a partners externos.
- El precio final, impuestos, tasas y condiciones pueden depender del partner.
- La referencia usa disclaimers sobre exactitud, disponibilidad y responsabilidad del tercero.
- Se observa una orientación a mostrar oportunidades y ahorro, pero esa comunicación exige contexto para no convertir un precio observado en una promesa de reserva.

### 2.5. Localización y responsive

- La localización española afecta labels, prompts y mensajes estructurales, no solo el título.
- La composición se adapta a layouts apilados y touch-friendly en viewport pequeño.
- La navegación dinámica puede estar condicionada por protección anti-bot o por la forma de acceso; cualquier patrón técnico debe revalidarse con navegador real.

## 3. Inferencias, no hechos garantizados

Estas conclusiones son hipótesis de producto derivadas de la observación y no deben tratarse como capacidades comprobadas:

1. El modelo de negocio probablemente depende de referrals/afiliación o tráfico a partners.
2. El volumen de partners puede ser amplio, pero no se puede trasladar a Viru sin contrato, cobertura y coste comprobados.
3. La alerta puede apoyarse en captura de email y procesos externos, pero Viru debe diseñar su propio consentimiento, delivery y ownership.
4. Una UI simple de ocupación puede esconder complejidad en pasos posteriores; no debemos eliminar ocupación avanzada si rompe la comparabilidad.
5. Un mensaje de ahorro no implica que el precio sea histórico, final o universalmente disponible.

## 4. Patrones que sí llevamos a Viru

| Patrón | Traducción propuesta en Viru | Condición |
|---|---|---|
| Búsqueda protagonista | Destino + fechas + ocupación como foco de `/hoteles` | H03/H13 |
| Beneficio visible de tracking | CTA humano para seguir una oferta | H22/H23 |
| Alertas cerca de la decisión | Crear alerta desde resultado/detalle, no solo en settings | H26/H27 |
| Comparación con salida externa | Deeplink claro al partner con contexto y disclosure | H18/H19/H35 |
| Localización completa | ES/EN en labels, errores, fechas, moneda, emails y estados | H34 |
| Responsive apilado | Mobile-first para formulario, filtros, cards y tracking | H31-H33 |
| Lenguaje de ahorro | Mostrar delta solo cuando baseline y condiciones sean comparables | H19/H24/H25 |
| Transparencia de intermediario | Explicar que reserva y precio final viven en partner | H35/H50 |

## 5. Patrones que no debemos copiar directamente

1. **“Avisar cuando baje” sin confirmar el canal:** en Viru debe indicar si el aviso será inbox, email, push o solo disponibilidad futura.
2. **Promesa genérica de precio:** debemos mostrar freshness, provider y condiciones.
3. **Simplificación excesiva de habitaciones/personas:** una búsqueda rápida no debe producir una oferta incompatible.
4. **Ranking opaco:** no colocar una oferta arriba por afiliación sin política explícita.
5. **Disclaimers como sustituto de UX:** la transparencia debe aparecer junto al precio, no enterrada solo en legal.
6. **Dependencia de un número amplio de partners:** Viru debe poder degradar y explicar cobertura por mercado.
7. **Imitación visual:** mantener identidad Viru Warm-Luxe, no clonar colores, marca ni composición.

## 6. Traducción a decisiones de producto Viru

### Decisión D1 — El tracking aparece antes de salir

La persona podrá guardar o seguir desde resultado/detalle. No tendrá que descubrir `/notifications` o una página secundaria para activar valor.

**Afecta:** H16, H18, H22, H23, H27.

### Decisión D2 — El CTA visible será “Seguir precio” solo para una oferta suficientemente definida

Si faltan fechas, ocupación, provider o precio comparable, el CTA debe pedir completar contexto o permitir “Guardar hotel” sin prometer tracking.

**Afecta:** H10, H19, H22, H23.

### Decisión D3 — “Precio observado” y “precio final del partner” serán conceptos distintos

La UI no llamará “precio final” a un valor que el partner todavía puede cambiar. Fees desconocidas se marcarán como desconocidas.

**Afecta:** H05, H19, H35.

### Decisión D4 — La señal de ahorro necesita baseline

“Bajó un 12 %” solo se muestra cuando existe comparación válida: snapshot anterior/inicial o baseline compatible, misma estancia, moneda y condiciones suficientes.

**Afecta:** H24-H26.

### Decisión D5 — La localización forma parte del contrato

No basta con traducir la cabecera. Se deben cubrir filtros, ocupación, alertas, estados parciales, freshness, fees, emails y deeplinks.

**Afecta:** H13, H21, H28, H34.

### Decisión D6 — Partner y afiliación se diseñan junto al resultado

Antes de optimizar clicks, Viru debe definir disclosure, atribución, deeplink seguro, cambios de precio y política de ranking.

**Afecta:** H18, H19, H35, H50.

## 7. Matriz de gaps Travel Price Drops → Viru

| Capacidad | Referencia | Estado/base Viru H00 | Próximo trabajo |
|---|---|---|---|
| Destino + fechas + ocupación | visible en búsqueda | área, fechas y huéspedes existen; ocupación avanzada debe validarse | H10-H15 |
| Aviso de bajada | visible en flujo | reglas/eventos/inbox existen; delivery externo no está probado como hotel | H26-H28 |
| Precio contextualizado | patrón de comparación | snapshots/rates existen; fees/total deben consolidarse | H19 |
| Partner/deeplink | intermediario | `deep_link` existe en rates, cobertura/seguridad deben validarse | H18/H35 |
| Localización | `lng=es` | i18n ES/EN existe en hoteles | H34 |
| Responsive | layout apilado | QA visual histórico documentado; repetir con baseline actual | H32/H40 |
| Meta-search de amplia cobertura | inferido/externo | Makcorps + mock; cobertura real pendiente | H07/H08 |
| Confianza histórica | no debe inferirse del marketing | señal parcial/paridad existe; confidence de tracking debe evolucionar | H05/H25 |

## 8. Preguntas que H03-H08 deben responder

1. ¿Qué campos son obligatorios para una oferta trackeable?
2. ¿Qué porcentaje de búsquedas reales puede resolver el provider actual por mercado?
3. ¿Qué significa “fresh” para una búsqueda y para un tracking?
4. ¿Qué canal de alertas existe hoy y cuál requiere integración externa?
5. ¿Qué fees devuelve cada provider y cómo se comparan?
6. ¿Qué deeplink puede abrirse de forma segura y atribuible?
7. ¿Cómo se informa una búsqueda parcial sin perder la confianza?
8. ¿Qué parte de la propuesta de Travel Price Drops es aplicable a Viru sin copiar su modelo comercial?

## 9. Evidencia y limitaciones del benchmark

- La observación está fechada el 2026-08-04 para evitar tratar el comportamiento externo como inmutable.
- La web externa puede cambiar, bloquear automatización o mostrar experiencias distintas por locale, user-agent, cookies o mercado.
- Este benchmark no es una auditoría legal ni una confirmación contractual de sus partners.
- Las referencias a afiliación, volumen de partners o mecanismos de backend son inferencias salvo cuando se indican como hechos visibles.
- El benchmark no sustituye browser QA de Viru ni pruebas con providers hoteleros reales.

## 10. Gate de H02

**Aprobado como benchmark funcional y de confianza.** H02 deja tres decisiones claras para las siguientes fases:

1. hacer del tracking una acción visible, pero no una promesa vacía;
2. mostrar precio y ahorro con condiciones/freshness/procedencia;
3. tratar localización, partner, responsive y estados degradados como parte del producto principal.

## 11. Handoff

- H03 debe convertir estos patrones en IA y wireflows de Viru.
- H05/H06 deben convertir confianza, freshness, provider y partial results en contratos.
- H13/H16/H22/H23 deben aplicar el patrón de tracking visible con semántica correcta.
- H19/H35/H50 deben resolver precio final, afiliación y deeplinks antes de optimizar conversión.
