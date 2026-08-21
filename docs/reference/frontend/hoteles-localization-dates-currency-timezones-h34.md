# H34 — Internacionalización, fechas, monedas y zonas horarias de `/hoteles`

**Estado:** completa como contrato de localización; remediación frontend, cobertura de claves y QA ES/EN pendientes  
**Fecha:** 2026-08-05  
**Área:** frontend / i18n / producto / accesibilidad / QA  
**Fuente de verdad:** sí para copy, locale, pluralización, fechas, monedas y timezones del módulo hotelero  
**Fase del roadmap:** H34  
**Depende de:** [H13 — formulario](../backend/hoteles-search-form-h13.md), [H16 — result cards](hoteles-result-cards-h16.md), [H23 — tracking desde oferta real](../backend/hoteles-real-offer-tracking-h23.md), [H27 — inbox y deep links](../backend/hoteles-private-inbox-deeplinks-h27.md)  
**Relacionado con:** [H19 — precio y fees](../backend/hoteles-price-total-fees-h19.md), [H21 — estados](hoteles-state-matrix-h21.md), [H25 — freshness/confidence](../backend/hoteles-freshness-confidence-actions-h25.md), H30 fechas flexibles, H31 visual, H32 responsive, H33 WCAG, H40 browser QA

> H34 no significa traducir unas cuantas etiquetas. Significa que una persona pueda leer, introducir y comparar una estancia hotelera en español o inglés sin mezclar idiomas, desplazar fechas por una zona horaria, interpretar mal una moneda o perder una acción por diferencias gramaticales.

## 1. Alcance y límites

H34 fija el contrato para:

1. diccionarios ES/EN, fallback y detección de locale;
2. copy de búsqueda, resultados, detalle, favoritos, tracking, histórico, alertas, paridad, cercanos y estados H21;
3. interpolaciones, pluralización y orden gramatical;
4. fechas de estancia frente a timestamps de captura/evento;
5. locale de números, importes, porcentajes y distancias;
6. moneda de origen, moneda preferida futura y límites de conversión;
7. timezone de usuario, provider y observación;
8. nombres propios, direcciones y contenido crudo del provider;
9. `lang`, accesibilidad, live regions y mensajes dinámicos;
10. matriz de tests y QA browser ES/EN.

H34 **no** implementa conversión de moneda, traducción automática de nombres/direcciones de proveedores, soporte global de locales, nuevos providers ni cambios de API. H19 define la semántica económica; H30 define fechas flexibles; H33 define el gate WCAG; H40 aportará la evidencia browser.

## 2. Estado actual comprobable

### 2.1. Infraestructura i18n existente

`frontend/src/i18n/index.ts` actualmente:

- soporta `Locale = "es" | "en"`;
- mapea `es → es-ES` y `en → en-US` mediante `localeTag`;
- resuelve primero locale explícito, después `localStorage` (`viru_locale`), navegador y finalmente español;
- `persistLocale` puede persistir el idioma y actualizar `document.documentElement.lang` en cliente, pero `useI18n` no lo invoca automáticamente en cada resolución/cambio: esto es un gap verificable de H34, no una capacidad ya garantizada;
- usa diccionarios estáticos ES/EN y fallback al diccionario español;
- devuelve la clave si falta también en el fallback;
- soporta pluralización simple `{ one, other }`, escogiendo `one` únicamente cuando `count === 1`.

Esto proporciona un buen bridge V1, pero no demuestra que cada rama hotelera tenga las mismas claves, interpolaciones, unidades y copy natural en ambos idiomas. El fallback a español o a una clave visible debe detectarse en QA, nunca aceptarse como experiencia final.

### 2.2. Cobertura hotelera existente

`frontend/src/i18n/domains/hotels.ts` ya contiene diccionarios amplios para:

- título, subtítulo y overview;
- búsqueda por nombre/zona, fechas, huéspedes, radio y provider;
- resultados, timeline, paridad y hoteles cercanos;
- watchlist/favoritos, seguimientos y snapshots;
- alertas, validaciones, reglas y eventos;
- mensajes de éxito/error y estados de demo.

Hay, no obstante, strings fuera de diccionario o con semántica incompleta:

- `HotelSearchPanel` formatea resultados de área con `Intl.NumberFormat("es-ES", ...)`, incluso cuando la UI está en inglés;
- `HotelTrackedOfferSnapshots` incluye `" · No disponible"` directamente en JSX;
- `formatDateShort()` usa `new Date(iso)` y no debe recibir `check_in`/`check_out` civiles `YYYY-MM-DD`, porque puede desplazarlos por timezone;
- el fallback `guestsOption` de español usa singular aunque el componente antepone cualquier `count`, y `trackedOffers.guests` usa plural fijo;
- algunos labels de provider/room/datos externos llegan tal cual y necesitan una política explícita de “dato propio” frente a “copy traducible”;
- el signo `—` se usa como fallback técnico en utilidades de formato y debe tener una lectura consistente.

### 2.3. Fechas y timezones actuales

La base actual usa `Intl.DateTimeFormat(localeTag, ...)` y `toLocaleString(localeTag)` en timeline, alertas, watchlist, snapshots y detalle. No se pasa `timeZone` explícito y no todas las salidas se envuelven en `<time dateTime>`.

H34 separa dos familias que no pueden mezclarse:

| Tipo | Ejemplos | Regla canónica |
|---|---|---|
| Fecha de estancia | `check_in`, `check_out`, `YYYY-MM-DD`, noches | fecha civil del hotel/consulta; no convertir mediante `new Date("YYYY-MM-DD")` para pintar el día |
| Timestamp de observación | `collected_at`, `updated_at`, `created_at`, `observed_at` | instante ISO con zona; almacenar/transportar en UTC y presentar en timezone de usuario o timezone explícito del contexto |
| Hora de provider | ventana operativa o captura del proveedor | solo mostrar si existe timezone/origen documentado; no inventar localidad |

El browser local es una fuente razonable V1 para presentar timestamps de actividad, pero la ausencia de `timeZone` explícito debe quedar documentada y probarse en máquinas con zonas distintas. Una fecha de entrada del 10 de marzo no puede aparecer como 9 de marzo por el offset del navegador.

### 2.4. Monedas actuales

El backend y los tipos hoteleros transportan `currency`, y los componentes usan `Intl.NumberFormat(localeTag, { style: "currency", currency })` en varios lugares. En V1:

- se presenta la moneda observada/de origen del provider;
- no existe todavía un selector hotelero de moneda preferida ni conversión con tipo de cambio versionado;
- `useTrackedOffers` conserva `EUR` como fallback de compatibilidad cuando no hay tarifa elegida; ese valor debe quedar marcado como bridge/moneda inferida y nunca presentarse como moneda observada del provider;
- `HotelSearchPanel` tiene un `es-ES` hardcodeado que rompe el locale de presentación;
- no se debe llamar “precio convertido”, “precio final” o “moneda local” si el dato no lo respalda H19.

La moneda de origen y el locale de presentación son dimensiones distintas: `1,234.50 USD` puede presentarse con convenciones inglesas o españolas, pero no debe cambiar de USD a EUR sin una operación explícita y trazable.

## 3. Contrato de locale y fallback

### 3.1. V1 compatible

- Los únicos locales de producto soportados por H34 V1 son `es` y `en`.
- `localeTag` canónico sigue siendo `es-ES`/`en-US` hasta que producto apruebe otra variante.
- La preferencia se resuelve de forma determinista: selección explícita > preferencia persistida > navegador > `es`.
- `document.documentElement.lang` debe reflejar el locale activo después de hidratar y no quedar permanentemente en español al cambiar idioma.
- Un diccionario incompleto no puede degradar silenciosamente a español en una ruta de release: el test debe fallar o registrar la clave faltante.
- H34 no declara soporte global: el producto V1 soporta únicamente ES/EN y sus tags canónicos `es-ES`/`en-US`.
- La clave visible (`hotels.foo.bar`) es un error de cobertura, no un fallback aceptable para usuario.
- Nombres de hoteles, ciudades, países, direcciones y provider son datos propios/externos; se conservan, salvo que exista un mapping de producto aprobado.

### 3.2. V2 fuera de alcance de H34

- carga perezosa por locale o routing `/{locale}`;
- `Intl.PluralRules` completo para todas las categorías;
- locales regionales adicionales;
- moneda preferida con FX, timestamp de tasa, redondeo y disclosure;
- traducción automática o normalización lingüística de contenido provider;
- timezone preferida persistida por usuario, distinta del browser, con control visible.

## 4. Copy, interpolaciones y pluralización

### 4.1. Reglas de copy

- Todo copy de producto —estado, aria-label, placeholder, error, botón, badge, tooltip y live region hotelero— sale de `t()`; existe una allowlist explícita para datos externos como nombre de hotel, ciudad, dirección, país, provider y room label.
- No concatenar frases traducibles en TSX cuando el orden pueda cambiar: usar una clave con `{hotel}`, `{count}`, `{date}`, `{price}`, `{distance}` o `{currency}`.
- Los valores interpolados no deben contener copy traducible oculto ni enums técnicos.
- El copy debe mantener la terminología de `docs/reference/ui-visible-language-guide.md` y `DESIGN.md`.
- “Demo”, “última comprobación”, “señal limitada”, “sin historial” y “provider error” deben tener copy de producto, no nombres internos.
- Los nombres propios y direcciones no se traducen automáticamente; si el provider devuelve texto en otro idioma, se conserva y se marca solo cuando sea necesario para comprensión.

### 4.2. Pluralización mínima V1

Cada unidad contable debe tener al menos forma singular y plural en ambos diccionarios:

- huésped/huéspedes — guest/guests;
- noche/noches — night/nights;
- hotel/hoteles — hotel/hotels;
- proveedor/proveedores — provider/providers;
- resultado/resultados — result/results;
- snapshot/observación/registro cuando se muestre un count.

La clave debe recibir `count` y no insertar manualmente un plural fijo. `count = 0` usa la forma `other` y debe tener copy natural (“0 huéspedes”, “0 guests”). Si una frase requiere más reglas que one/other, se documenta como gap V2 en vez de fingir gramática completa.

### 4.3. Accesibilidad del copy dinámico

- `aria-label`, `aria-describedby`, `role=status` y `role=alert` usan el diccionario activo;
- las regiones live anuncian una frase completa, no una secuencia de fragmentos concatenados;
- los cambios de precio incluyen unidad y moneda cuando sean necesarios para entenderlos;
- un locale switch no deja aria-copy en el idioma anterior.

## 5. Fechas y zonas horarias

### 5.1. Fecha civil de estancia

Para `check_in`/`check_out` y fechas flexibles H30:

- conservar el valor canónico `YYYY-MM-DD` como fecha civil, no como instante UTC;
- presentar con `Intl.DateTimeFormat(localeTag, { dateStyle: ... })` a partir de partes/constructor local controlado, no `new Date("YYYY-MM-DD")` sin política;
- validar `check_out > check_in` y calcular noches sin depender del offset DST del navegador;
- mostrar el rango y las noches con copy traducible y plural correcto;
- si el hotel/provider tiene timezone y la estancia cruza DST, las noches siguen siendo diferencia de fechas civiles, no división de milisegundos.

### 5.2. Timestamps

Para capturas, alertas, snapshots y `updated_at`:

- backend almacena y API transporta ISO 8601 con offset o `Z`;
- frontend presenta por defecto en timezone del navegador en V1, con locale activo;
- cuando la hora del hotel/provider sea material, mostrar zona/abreviatura o explicación localizada;
- incluir `<time dateTime="...">` en salidas que representen un instante;
- no usar “hoy”, “ayer” o “hace X” sin una función locale-aware y una política de reloj/timezone;
- tests deben congelar reloj y timezone para evitar snapshots inestables;
- invalid/null/unknown no se presenta como fecha válida: usa copy traducible de dato desconocido.

### 5.3. Timezone de datos

H34 distingue:

- `user_timezone`: zona de presentación de actividad en V1, derivada del navegador;
- `property_timezone`: zona del hotel si existe y está validada;
- `provider_observed_timezone`: zona declarada por origen si se conserva;
- `unknown`: ausencia de evidencia, nunca rellenada por suposición.

No se debe afirmar “comprobado a las 18:00 en Madrid” si solo existe un timestamp UTC sin zona contextualizada. La UI puede mostrar la hora local del usuario como “comprobado a las 18:00 (tu hora)” cuando producto lo apruebe.

## 6. Monedas, números y unidades

### 6.1. Moneda de origen V1

- `formatPrice` recibe valor, código ISO 4217 y locale de presentación;
- el código de moneda debe validarse o caer a un formato seguro con código visible, no romper `Intl` ni ocultar la unidad;
- no se redondea antes de decidir comparabilidad; el redondeo visual no altera el valor usado en tracking/alertas;
- importe, moneda y semántica de total/noches siguen H19;
- una tarifa sin moneda válida queda `unknown/unavailable`, no se muestra como EUR por defecto salvo bridge V1 explícitamente etiquetado.

### 6.2. Locale de presentación

- sustituir todo `Intl.NumberFormat("es-ES", ...)` hotelero por `localeTag` activo;
- porcentajes usan `style: "percent"` o formato documentado, sin duplicar `%` accidentalmente;
- distancias usan número locale-aware y unidad traducible (`km` si el contrato actual es métrico);
- separadores decimales y de millares cambian con locale, pero el código ISO permanece reconocible;
- el símbolo de moneda no es suficiente cuando puede ser ambiguo: conservar código en tooltip/aria o copy de contexto cuando proceda.

### 6.3. Conversión futura

H34 no aprueba FX. Una futura conversión debe definir: moneda preferida, tasa y timestamp, fuente, redondeo, fees, comparabilidad, cache, disclosure y comportamiento offline/error.

## 7. Matriz de superficies

| Superficie | Copy localizado | Fecha/número | Riesgo actual | Gate |
|---|---|---|---|---|
| Buscador | labels, placeholders, modo, provider, loading/error | fechas de estancia y huéspedes | plural y validación | ES/EN sin claves, fechas civiles correctas |
| Resultados | título, empty, precio sin dato, stars, distancia | importe origen + locale activo | `es-ES` hardcodeado en área | inglés no muestra formato español |
| Detalle | selección, dirección externa, última captura | timestamp + `<time>`/timezone | `toLocaleString` sin política | captura comprensible y no desplazada |
| Watchlist | guardado, quitar, unavailable | created_at timestamp | copy/error parcial | estado y fecha localizados |
| Tracking | estado, precios, fechas, historial | estancia civil + importes + timestamps | plural fijo y moneda fallback | oferta reconstruible en ambos idiomas |
| Snapshots | loading, empty, unavailable, provider | collected_at timestamp | “No disponible” hardcodeado; error→empty | error y estado localizado |
| Alertas | tipos, umbrales, validación, eventos | importe, porcentaje, created_at | summaries sin unidad monetaria en algunos casos | regla entendible sin contexto visual |
| Paridad | labels, provider count, lowest/highest/spread | moneda origen + porcentaje | plural provider fijo | comparación no parece convertida |
| Cercanos/comp set | añadir/quitar, distancia, errores | km locale-aware | textos externos y fallbacks | acción y unidad claras |
| Live regions | loading, error, resultados, cambios | valores completos | estrategia H33 pendiente | una frase activa, sin mezcla |

## 8. Prioridades de remediación

### P0 — antes de declarar H34 cerrada

1. Eliminar hardcodes de locale/copy en superficies hoteleras, empezando por `Intl.NumberFormat("es-ES")` y `"No disponible"`.
2. Garantizar que cada clave hotelera usada en TSX existe en ES y EN con los mismos placeholders.
3. Separar fechas civiles de estancia de timestamps y congelar tests con timezone/reloj controlados.
4. Asegurar que cambios de locale actualizan `document.documentElement.lang`, copy visible, aria-copy y formatos sin mezclar idiomas.
5. Mantener moneda de origen visible y no prometer conversión inexistente.

### P1 — antes de release hotelero

1. Completar pluralización de huéspedes, noches, resultados, hoteles y providers.
2. Añadir `<time>` y política de timezone a capturas, alertas, snapshots y detalle.
3. Hacer locale-aware números, porcentajes y distancias en todas las ramas.
4. Diferenciar moneda desconocida, fallback EUR de bridge y moneda observada.
5. Probar copy largo ES/EN junto con H32/H33: labels, aria, errors, empty, stale y provider warnings.
6. Verificar que nombres/direcciones provider no se traducen ni se presentan como copy de Viru.

### P2 — evolución

1. `Intl.PluralRules` y más categorías si aparecen idiomas nuevos.
2. Selector de timezone o preferencia persistida, si el producto lo necesita.
3. Conversión FX versionada con disclosure y contract tests.
4. Locales regionales adicionales y estrategia de fallback por dominio.
5. Traducción humana revisada de contenido dinámico si algún provider lo exige.

## 9. Tests y evidencia

### Tests automáticos

- comparar las claves y placeholders del dominio hoteles ES/EN;
- fallar ante claves devueltas literalmente o fallback silencioso en rutas hoteleras;
- verificar `es-ES`/`en-US` para el mismo importe y que el área no fuerce español;
- comprobar singular/plural con 0, 1, 2 y valores grandes;
- probar fechas `YYYY-MM-DD` alrededor de medianoche y DST sin cambiar el día de estancia;
- probar timestamps con UTC, offsets distintos, null e invalid;
- comprobar que `document.documentElement.lang` sigue locale activo;
- verificar que copy aria/live existe en ambos idiomas;
- comprobar que moneda USD/EUR/GBP se conserva como origen y que no hay conversión implícita;
- verificar porcentajes, distancias, separadores y redondeo visual;
- detectar strings hoteleros hardcodeados fuera de allowlist de datos propios.

### Browser/manual

Para ES y EN, 360/390/414/768/1024/desktop, dark/light y timezone al menos UTC, Europe/Madrid y America/New_York:

1. cambiar idioma desde el control y recorrer búsqueda, resultados, detalle, tracking y alertas;
2. verificar que no aparece una frase española en inglés ni una clave técnica en ninguna región;
3. introducir fechas alrededor de cambio horario y confirmar que la estancia no cambia de día;
4. revisar capturas, alertas y snapshots con zona/locale comprensibles;
5. comprobar precios en USD/EUR y porcentajes sin conversión ni símbolos ambiguos;
6. probar 0/1/2 huéspedes, noches, providers y resultados;
7. provocar empty, partial, stale, provider error y auth, incluyendo copy aria de H21/H33;
8. usar zoom 200% y nombres largos en ambos idiomas sin overflow;
9. inspeccionar `lang`, `<time>`, aria labels y live regions en árbol accesible;
10. guardar evidencia de locale, timezone, moneda de origen, fixture y consola.

## 10. Gate H34

H34 podrá marcarse implementada cuando:

1. ES y EN cubran todas las claves y placeholders hoteleros sin fallback visible;
2. ninguna superficie hotelera fuerce `es-ES` cuando el locale activo sea inglés;
3. fechas de estancia no sufran desplazamiento por timezone y timestamps tengan política explícita;
4. `document.documentElement.lang`, copy visible, labels, aria y live regions estén sincronizados;
5. pluralización e interpolaciones sean naturales para 0/1/2+;
6. números, porcentajes, distancias e importes usen locale y unidad correctos;
7. moneda de origen, moneda desconocida y cualquier fallback V1 estén diferenciados, sin FX implícito;
8. nombres/direcciones/provider se conserven como datos externos y no se presenten como traducción inventada;
9. empty/error/partial/stale/auth y copy de accesibilidad estén localizados en ambos idiomas;
10. tests automáticos y QA manual pasen en los locales/timezones/temas/viewports definidos;
11. el cierre H34 no se confunda con soporte global, conversión de divisas, traducción de providers ni cierre WCAG H33/browser QA H40; no se declara soporte global.

**Resultado contractual:** H34 define la localización hotelera V1 honesta y su evolución V2. La base ES/EN existe, pero la implementación actual conserva gaps de locale hardcodeado, pluralización, fechas civiles, timezone explícito y copy incrustado; la fase no se considera implementada hasta superar el gate.
