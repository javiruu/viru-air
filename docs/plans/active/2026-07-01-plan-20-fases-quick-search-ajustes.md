# Plan progresivo de 20 fases — Quick Search + Ajustes activos

**Proyecto:** Viru Air
**Pantalla:** `/quick-search` / “Búsqueda rápida”
**Objetivo:** reducir fricción cognitiva, separar búsqueda de filtros de resultados y convertir “Ajustes activos” en un sistema compacto, progresivo y entendible.
**Nivel de riesgo:** medio-alto si se intenta de golpe; bajo si se ejecuta fase a fase.
**Regla principal:** una fase = un cambio visible acotado + QA real + commit pequeño.

---

## 0. Contexto y dirección de producto

La auditoría previa concluye que la pantalla actual tiene un conflicto fuerte:

> Se llama “Búsqueda rápida”, pero se comporta como un panel avanzado.

El objetivo no es eliminar potencia. El objetivo es **mover la complejidad al momento correcto**.

### Decisión base

La pantalla debe evolucionar hacia este modelo:

1. **Formulario rápido visible**
   - Origen.
   - Destino.
   - Aeropuertos cercanos.
   - Pasajeros.
   - Fecha.
   - Margen de fecha.
   - Buscar vuelos.

2. **Resumen compacto de ajustes**
   - Chips pequeños y editables.
   - Nada de cards grandes para explicar cada ajuste en el primer nivel.

3. **Más opciones**
   - Avanzado, pero accesible.
   - Horarios.
   - Evitar aeropuertos.
   - Vuelos separados.
   - Información incompleta.

4. **Filtros después de resultados**
   - Precio.
   - Duración.
   - Ordenación.
   - Visualización.

5. **Rescate contextual si no hay resultados**
   - “Probar ±1 día”.
   - “Buscar aeropuertos cercanos”.
   - “Ampliar al máximo”.
   - “Más opciones”.

---

## 1. Reglas globales para Codex

Estas reglas aplican a todas las fases.

### 1.1. Ritmo de trabajo obligatorio

Codex debe trabajar así:

1. Leer el objetivo de la fase.
2. Inspeccionar componentes actuales.
3. Hacer el cambio mínimo.
4. Ejecutar QA indicado.
5. Capturar evidencia visual si hay cambio visible.
6. Hacer commit pequeño.
7. Parar y reportar.

**No se permite ejecutar dos fases a la vez salvo instrucción explícita.**

### 1.2. Restricciones duras

Codex no puede:

- rediseñar toda la pantalla de golpe;
- cambiar contratos de backend sin permiso;
- renombrar parámetros API si no es estrictamente interno al frontend;
- eliminar funcionalidad avanzada;
- mover filtros al backend sin revisar contrato;
- introducir librerías UI nuevas;
- convertir Viru en un dashboard SaaS genérico;
- cambiar rutas canónicas;
- tocar pantallas no relacionadas salvo dependencias compartidas muy justificadas;
- hacer refactors globales “aprovechando”;
- mezclar cambios de copy, layout y lógica en una fase si no toca.

### 1.3. Obligaciones de identidad visual

Cada fase debe preservar:

- calidez;
- personalidad aeronautica;
- jerarquía clara;
- estilo premium cercano;
- compatibilidad light/dark;
- microcopy humano;
- foco visible;
- accesibilidad básica.

### 1.4. Separación conceptual obligatoria

Codex debe mantener separados estos grupos:

| Grupo | Qué significa | Dónde vive |
|---|---|---|
| Datos de búsqueda | Cambian lo que Viru consulta | Formulario principal o Más opciones |
| Ajustes flexibles | Amplían ruta/fecha | Formulario principal compacto |
| Ajustes avanzados | Reglas menos frecuentes | Modal/acordeón avanzado |
| Filtros de resultados | Ordenan o filtran lo encontrado | Después de buscar |
| Rescate sin resultados | Sugerencias contextuales | Empty state / no-results |

### 1.5. Términos prohibidos en UI visible

No debe quedar texto visible con estos términos:

- contrato backend;
- datos parciales;
- self-connect;
- buffer;
- cobertura;
- modo estricto;
- degradado;
- frescura;
- límites, salvo que esté muy contextualizado;
- reglas, salvo que se renombre a preferencias o “qué vuelos te valen”.

### 1.6. Términos recomendados

| Técnico / actual | Usuario normal |
|---|---|
| Cobertura | Aeropuertos cercanos |
| Radio alternativo | Distancia máxima |
| Datos parciales | Información incompleta |
| Self-connect | Vuelos separados |
| Buffer mínimo | Tiempo mínimo entre vuelos |
| Máxima cobertura | Ampliar al máximo |
| Reglas del viaje | Qué vuelos te valen |
| Vista de resultados | Filtros de resultados |
| Solo resultados que cumplan tus límites | Solo mostrar vuelos que encajen |

---

## 2. Estrategia de implementación

### 2.1. Por qué 20 fases

El objetivo es evitar que Codex haga un “mega-rediseño” difícil de revisar.
Las 20 fases separan:

- copy;
- jerarquía;
- estado;
- componentes;
- layout;
- responsive;
- QA;
- limpieza final.

### 2.2. Política de commits

Un commit por fase.

Formato recomendado:

```bash
feat(quick-search): fase 01 baseline visual audit
fix(quick-search): fase 04 improve search cta hierarchy
refactor(quick-search): fase 09 extract advanced settings shell
```

### 2.3. Política de rollback

Cada fase debe poder revertirse con un único commit.

No se aceptan fases que dejen el sistema a medias sin fallback visible.

### 2.4. QA mínimo por fase

Cada fase debe indicar:

- comando de build/typecheck/lint si aplica;
- test unitario o e2e si existe;
- captura desktop light;
- captura desktop dark si cambia UI;
- captura móvil si cambia layout;
- interacción manual probada.

### 2.5. Criterio de avance

No pasar a la fase siguiente si:

- hay error de TypeScript;
- hay overflow horizontal;
- el CTA Buscar pierde prioridad;
- se rompe el submit;
- no hay evidencia visual del cambio;
- el texto visible mezcla ES/EN sin motivo;
- aparecen términos técnicos prohibidos.

---

# Fase 1 — Inventario real de la pantalla actual

## Objetivo

Crear una base de verdad antes de tocar nada. Codex debe entender qué componentes, estados y props gobiernan Quick Search y Ajustes activos.

## Cambios permitidos

- Ningún cambio funcional.
- Solo se permite añadir documentación temporal o reporte markdown si hace falta.

## Cambios prohibidos

- No modificar componentes.
- No cambiar CSS.
- No renombrar textos.
- No mover campos.

## Tareas

1. Localizar el componente principal de `/quick-search`.
2. Localizar componentes relacionados con:
   - origen;
   - destino;
   - fecha;
   - pasajeros;
   - ajustes activos;
   - modal/acordeón si existe;
   - resultados;
   - empty state.
3. Mapear estado actual:
   - nombre de variables;
   - query params;
   - defaults;
   - sincronización con preferencias.
4. Identificar si “Ajustes activos” es:
   - componente propio;
   - markup inline;
   - derivado de configuración compartida;
   - duplicado en otras pantallas.
5. Revisar dependencias de tests existentes.

## QA

- Ejecutar:
  - `npm run typecheck` si existe.
  - `npm run lint` si existe.
  - tests específicos si existen para quick-search.
- Abrir `/quick-search`.
- Capturar:
  - desktop light baseline;
  - desktop dark baseline;
  - móvil baseline.

## Criterios de aceptación

- Existe un mapa claro de archivos tocables.
- No se ha modificado comportamiento.
- Se sabe qué piezas son seguras para tocar en fases posteriores.
- Queda documentado si hay acoplamiento con backend/query params.

## Resultado esperado

Un reporte interno tipo:

```md
## Quick Search inventory
- Main component:
- Active settings component:
- Search payload builder:
- Result filters:
- Empty state:
- Tests:
- Risks:
```

---

# Fase 2 — Limpieza de microcopy técnico sin mover layout

## Objetivo

Reducir fricción inmediata sin tocar estructura. Esta fase es segura y pequeña: cambia textos visibles problemáticos, pero deja todo en el mismo lugar.

## Cambios permitidos

- Renombrar labels.
- Renombrar ayudas.
- Renombrar botones secundarios.
- Eliminar frases puramente internas.

## Cambios prohibidos

- No mover campos.
- No cambiar lógica.
- No ocultar ajustes.
- No tocar payload enviado al backend.

## Sustituciones obligatorias

| Actual | Nuevo |
|---|---|
| Cobertura | Aeropuertos cercanos |
| Radio alternativo (km) | Distancia máxima |
| Datos parciales permitidos | Mostrar vuelos con información incompleta |
| Self-connect | Vuelos separados |
| Buffer mínimo (min) | Tiempo mínimo entre vuelos |
| Reglas del viaje | Qué vuelos te valen |
| Vista de resultados | Filtros de resultados |
| Solo resultados que cumplan tus límites | Solo mostrar vuelos que encajen |
| Máxima cobertura | Ampliar al máximo |

## Microcopy recomendado

### Ajustes activos

Antes:

> Organiza cobertura, reglas y vista sin perder contexto.

Después:

> Revisa cómo busca Viru y qué vuelos te muestra.

### Aeropuertos cercanos

> Útil si puedes salir o llegar desde otro aeropuerto para encontrar mejores opciones.

### Vuelos separados

> Viru puede combinar vuelos que no van en la misma reserva. Puede salir más barato, pero la conexión corre por tu cuenta.

### Tiempo mínimo entre vuelos

> Deja margen para bajar del avión, recoger equipaje si hace falta y volver a embarcar.

## QA

- Buscar textos prohibidos en el frontend:
  - `contrato backend`
  - `self-connect`
  - `buffer`
  - `datos parciales`
  - `cobertura`
- Verificar pantalla en light/dark.
- Verificar que los campos siguen enviando los mismos valores.

## Criterios de aceptación

- No queda microcopy técnico visible.
- No ha cambiado la posición de ningún bloque.
- No se rompe el submit.
- La pantalla sigue funcionando igual, pero se entiende mejor.

---

# Fase 3 — Reforzar CTA “Buscar vuelos” sin reordenar campos

## Objetivo

Hacer que el botón principal recupere jerarquía visual antes de mover nada.

## Cambios permitidos

- Ajustar tamaño, peso visual y posición local del CTA.
- Cambiar label de “Buscar” a “Buscar vuelos”.
- Mejorar estado disabled/loading.
- Mejorar ayuda debajo del CTA.

## Cambios prohibidos

- No mover todavía “Ajustes activos”.
- No eliminar ningún ajuste.
- No cambiar orden general del formulario.

## Requisitos visuales

El CTA debe:

- ser el elemento interactivo más importante del panel;
- estar claramente separado de acciones secundarias;
- mantener estilo Viru, no botón SaaS plano;
- tener estado hover/focus;
- tener estado loading claro.

## Copy recomendado

Botón:

> Buscar vuelos

Ayuda debajo:

> Viru buscará con la ruta y fecha que has elegido.

Si hay aeropuertos cercanos activos:

> Viru también mirará aeropuertos cercanos dentro de la distancia elegida.

## QA

- Verificar tab order hasta el botón.
- Verificar enter/click submit.
- Verificar disabled si faltan campos obligatorios.
- Verificar loading si existe.
- Captura desktop light/dark.

## Criterios de aceptación

- El botón Buscar ya no parece una acción secundaria.
- No hay dos CTAs primarios compitiendo.
- El usuario puede identificar dónde termina el formulario.

---

# Fase 4 — Crear modelo de chips compacto sin sustituir el bloque actual

## Objetivo

Preparar el reemplazo de “Ajustes activos” sin riesgo. Primero se crea un componente de chips compacto, visible en modo experimental o debajo del bloque actual.

## Cambios permitidos

- Crear componente nuevo:
  - `QuickSearchSummaryChips`
  - o nombre equivalente.
- Derivar chips desde el estado actual.
- Mostrarlo bajo el formulario o bajo Ajustes activos, pero sin eliminar nada todavía.

## Cambios prohibidos

- No eliminar el bloque actual.
- No mover campos.
- No cambiar lógica de ajustes.

## Chips mínimos

Debe soportar:

- Ruta exacta.
- Cerca del origen.
- Cerca del destino.
- Hasta X km.
- Fecha exacta.
- ±1 día.
- ±2 días.
- X pasajeros.
- Vuelos separados activados.
- Información incompleta permitida.
- Evita MAD, BCN.

## Reglas de chips

- Solo mostrar chips relevantes.
- No mostrar chips redundantes.
- No mostrar “0 ajustes”.
- Si hay más de 4 chips en móvil, permitir wrap limpio.
- Chips avanzados deben ser neutrales, no alarmistas.

## QA

- Probar estados:
  - exacta sin flex;
  - origen cercano;
  - destino cercano;
  - ambos cercanos;
  - radio personalizado;
  - margen de fecha;
  - pasajeros > 1.
- Captura desktop/móvil.

## Criterios de aceptación

- Los chips reflejan el estado real.
- No se rompe “Ajustes activos”.
- No hay duplicidad confusa: el chip summary debe parecer secundario mientras convive con el bloque viejo.

---

# Fase 5 — Reducir visualmente el bloque “Ajustes activos”

## Objetivo

Bajar peso visual del bloque antiguo sin cambiar todavía su contenido. Es una fase puente.

## Cambios permitidos

- Reducir altura/padding.
- Reducir énfasis de cards internas.
- Convertir cabecera en más compacta.
- Dejar el bloque como “revisión secundaria”.
- Reforzar chips como resumen principal.

## Cambios prohibidos

- No eliminar contenido aún.
- No mover campos fuera.
- No cambiar agrupaciones internas todavía.

## Requisitos

El bloque “Ajustes activos” debe pasar a sentirse como:

> “Puedes revisar más detalles si quieres”

y no como:

> “Tienes que configurar todo esto antes de buscar”.

## QA

- Comparar captura fase 1 vs fase 5.
- Verificar que Buscar domina sobre Ajustes activos.
- Verificar que las cards no parecen igual de importantes que el CTA.

## Criterios de aceptación

- Menor peso visual.
- Mismo contenido disponible.
- No se pierde funcionalidad.
- El bloque deja de competir con el formulario principal.

---

# Fase 6 — Colapsar “Ajustes activos” por defecto

## Objetivo

Hacer que “Ajustes activos” deje de ocupar espacio mental de entrada.

## Cambios permitidos

- Convertir el bloque actual en acordeón colapsado.
- Mantener chips visibles.
- Añadir botón:
  - “Ver ajustes”
  - “Más opciones”
  - “Editar ajustes”
- Persistir estado abierto/cerrado solo si ya existe patrón seguro; si no, no persistir.

## Cambios prohibidos

- No mover todavía cada ajuste a su ubicación final.
- No eliminar campos.
- No cambiar payload.

## Comportamiento

Estado inicial recomendado:

- cerrado si no hay ajustes avanzados activos;
- abierto si viene de preferencias con varios ajustes avanzados activos;
- abierto si hay error de validación dentro.

## Copy

Título compacto:

> Ajustes de búsqueda

Subtítulo:

> Tienes la búsqueda en modo exacto. Puedes ampliarla si lo necesitas.

Con flex activo:

> Viru también está mirando aeropuertos cercanos.

## QA

- Abrir/cerrar acordeón.
- Verificar teclado.
- Verificar foco.
- Verificar móvil.
- Verificar que campos dentro siguen funcionando.

## Criterios de aceptación

- La pantalla inicial reduce altura.
- El usuario ve chips + CTA sin tragarse todo el panel.
- Ningún ajuste queda inaccesible.

---

# Fase 7 — Separar visualmente “cambia búsqueda” de “solo resultados”

## Objetivo

Empezar a corregir el modelo mental. Todavía dentro del bloque colapsable, pero separando claramente lo que cambia la búsqueda de lo que solo afecta resultados.

## Cambios permitidos

- Reagrupar secciones dentro del acordeón.
- Cambiar títulos internos.
- Añadir divisores o subtítulos.
- Sin mover filtros fuera todavía.

## Cambios prohibidos

- No cambiar lógica.
- No eliminar campos.
- No crear modal todavía.

## Nueva agrupación interna

1. **Dónde puede buscar Viru**
   - ruta exacta;
   - origen cercano;
   - destino cercano;
   - distancia máxima;
   - excluir aeropuertos.

2. **Qué vuelos te valen**
   - hora desde;
   - hora hasta;
   - vuelos separados;
   - escalas;
   - tiempo mínimo entre vuelos.

3. **Cómo ver resultados**
   - precio;
   - duración;
   - ordenar;
   - información incompleta.

## QA

- Verificar que todos los campos siguen apareciendo.
- Verificar que el usuario puede entender los grupos sin leer ayudas largas.
- Buscar textos técnicos prohibidos.

## Criterios de aceptación

- La separación conceptual es visible.
- El bloque todavía no cambia comportamiento.
- Se prepara la migración progresiva posterior.

---

# Fase 8 — Sacar “ordenar por” del pre-submit y ponerlo junto a resultados

## Objetivo

Primer movimiento real: “Ordenar por” deja de vivir antes de buscar y pasa a la zona de resultados.

## Cambios permitidos

- Mover control de ordenación a la cabecera/listado de resultados.
- Mantener valor por defecto.
- Si no hay resultados, ocultarlo o dejarlo disabled.
- Mantener query/state si ya existía.

## Cambios prohibidos

- No mover precio/duración todavía.
- No cambiar algoritmo de orden.
- No tocar backend.

## Reglas

- Si no hay resultados: no mostrar “Ordenar por”.
- Si hay resultados: mostrarlo como filtro secundario.
- Debe quedar claro que ordena lo encontrado, no amplía búsqueda.

## QA

- Buscar una ruta con resultados.
- Cambiar orden.
- Confirmar que la lista cambia o que el estado se actualiza.
- Buscar sin resultados.
- Confirmar que no aparece ordenación inútil.

## Criterios de aceptación

- “Ordenar por” ya no mete ruido antes de buscar.
- La funcionalidad sigue disponible.
- No se rompe Watchlist ni acciones de resultado.

---

# Fase 9 — Mover precio mínimo/máximo a filtros de resultados

## Objetivo

Sacar filtros de precio del panel pre-búsqueda.

## Cambios permitidos

- Mover precio mínimo y máximo a zona de resultados.
- Mostrar solo cuando hay resultados.
- Mantener estado si el usuario ya tenía valores.
- Añadir chip si hay filtro de precio activo.

## Cambios prohibidos

- No cambiar búsqueda backend salvo que el filtro ya se aplicara localmente.
- No mezclar con duración todavía.
- No borrar valores guardados sin aviso.

## Decisión de producto

Precio es un filtro de resultados, no una condición mental antes de buscar.
El usuario no debería pensar en precio mínimo antes de ver vuelos.

## Copy

Título:

> Filtrar resultados

Labels:

- Precio mínimo
- Precio máximo

Ayuda opcional:

> Se aplica sobre los vuelos encontrados.

## QA

- Sin resultados: no aparece filtro de precio.
- Con resultados: aparece filtro de precio.
- Cambiar máximo y verificar resultados filtrados.
- Limpiar filtros y verificar restauración.

## Criterios de aceptación

- Precio ya no compite con búsqueda rápida.
- Si el precio afecta a la lista, el chip lo refleja.
- El usuario puede limpiar el filtro.

---

# Fase 10 — Mover duración máxima a filtros de resultados

## Objetivo

Completar la salida de filtros de resultado básicos del pre-submit.

## Cambios permitidos

- Mover duración máxima junto a precio.
- Añadir chip activo.
- Mantener comportamiento local si ya existía.

## Cambios prohibidos

- No cambiar semántica backend sin revisión.
- No mover “hora salida” en esta fase.
- No mezclar con escalas.

## Copy

Label:

> Duración máxima

Ayuda:

> Oculta vuelos más largos dentro de los resultados encontrados.

## QA

- Buscar con resultados.
- Aplicar duración máxima.
- Limpiar duración.
- Verificar móvil.
- Verificar que el submit no depende de este campo.

## Criterios de aceptación

- Duración ya no aparece antes de buscar.
- El filtro se entiende como post-búsqueda.
- No hay pérdida de estado al buscar de nuevo salvo comportamiento ya existente.

---

# Fase 11 — Crear shell de “Más opciones” sin mover contenido final todavía

## Objetivo

Crear el contenedor futuro para ajustes avanzados.

## Cambios permitidos

- Añadir botón “Más opciones”.
- Añadir modal, drawer o acordeón avanzado.
- Crear estructura con secciones vacías o copiadas de forma no destructiva.
- Mantener bloque antiguo como fuente principal si hace falta.

## Cambios prohibidos

- No mover todavía todos los campos.
- No eliminar el acordeón viejo aún.
- No cambiar payload.

## Modal vs acordeón

Preferencia:

- Desktop: modal/panel lateral amplio si ya hay patrón.
- Móvil: full-screen sheet o acordeón claro.
- Si no hay infraestructura segura: acordeón dentro del panel.

## Secciones objetivo

- Aeropuertos.
- Horarios.
- Vuelos separados.
- Filtros de resultados.

## QA

- Abrir/cerrar.
- Escape/click outside si modal.
- Focus trap si modal.
- Tab order.
- Móvil.
- Dark/light.

## Criterios de aceptación

- Existe entrada clara a opciones avanzadas.
- No rompe el flujo rápido.
- No duplica visualmente demasiadas cosas.

---

# Fase 12 — Mover exclusiones IATA a “Más opciones”

## Objetivo

Sacar “Excluir orígenes/destinos” del primer nivel.

## Cambios permitidos

- Mover campos de exclusión al shell avanzado.
- Cambiar labels a lenguaje humano.
- Mantener soporte IATA como ayuda, no como concepto principal.

## Cambios prohibidos

- No quitar funcionalidad.
- No validar de forma más estricta si no existía.
- No cambiar formato enviado.

## Copy

Labels:

- Aeropuertos de salida que no quieres usar
- Aeropuertos de llegada que no quieres usar

Placeholder:

- MAD, BCN
- DUB, LIS

Ayuda:

> Escribe códigos IATA separados por coma. Útil si hay aeropuertos que prefieres evitar.

## QA

- Introducir exclusiones.
- Ver chips “Evita MAD, BCN”.
- Buscar y verificar payload/estado.
- Limpiar exclusiones.
- Validar móvil.

## Criterios de aceptación

- Las exclusiones ya no aparecen en el formulario inicial.
- Siguen accesibles para usuarios avanzados.
- Se reflejan en chips si están activas.

---

# Fase 13 — Mover horarios de salida a “Más opciones”

## Objetivo

Mover “Salida desde/hasta” a ajustes avanzados.

## Cambios permitidos

- Mover campos al grupo “Horarios”.
- Cambiar copy.
- Mostrar chip solo si hay horario activo.

## Cambios prohibidos

- No cambiar formato horario.
- No cambiar validación salvo mensajes.
- No mezclar con fecha.

## Copy

Grupo:

> Horarios

Labels:

- Salir después de
- Salir antes de

Ayuda:

> Útil si quieres evitar vuelos demasiado temprano o demasiado tarde.

Chip:

- Sale después de 08:00
- Sale antes de 22:00

## QA

- Añadir horario.
- Ver chip.
- Buscar.
- Limpiar.
- Validar error si desde > hasta, si aplica.
- Ver móvil.

## Criterios de aceptación

- Horarios fuera del primer nivel.
- Estado visible si activo.
- Validación no empeora.

---

# Fase 14 — Mover vuelos separados y tiempo mínimo a “Más opciones”

## Objetivo

Ocultar self-connect/vuelos separados por defecto y explicarlo humanamente.

## Cambios permitidos

- Mover toggle de vuelos separados al grupo avanzado.
- Mostrar máximo de escalas y tiempo mínimo solo si se activa.
- Añadir aviso claro.

## Cambios prohibidos

- No activar vuelos separados por defecto.
- No ocultar aviso de riesgo.
- No cambiar cálculo backend.

## Copy

Toggle:

> Combinar vuelos separados

Ayuda:

> Viru puede unir vuelos que no van en la misma reserva. Puede salir más barato, pero la conexión corre por tu cuenta.

Campos condicionales:

- Máximo de vuelos separados
- Tiempo mínimo entre vuelos

Aviso:

> Revisa bien el margen. Si el primer vuelo se retrasa, la segunda reserva puede no estar protegida.

## QA

- Por defecto: campos condicionales ocultos.
- Activar: aparecen campos.
- Desactivar: campos desaparecen o quedan inactivos.
- Estado se refleja en chips.
- Buscar con toggle activo.
- Verificar payload.

## Criterios de aceptación

- El usuario medio no ve este bloque.
- El usuario avanzado entiende el riesgo.
- No hay terminología técnica visible.

---

# Fase 15 — Convertir “Aeropuertos cercanos” en banda principal compacta

## Objetivo

Dar protagonismo a lo verdaderamente útil: origen/destino cercanos.

## Cambios permitidos

- Crear una banda visible bajo origen/destino.
- Incluir toggles/chips:
  - Cerca del origen.
  - Cerca del destino.
- Mostrar distancia máxima si alguno activo.

## Cambios prohibidos

- No meter escalas ni exclusiones aquí.
- No mostrar todas las opciones de cobertura.
- No usar “Cobertura” como label visible.

## Layout recomendado

Debajo de origen/destino:

```txt
Aeropuertos cercanos
[ Cerca del origen ] [ Cerca del destino ]     Distancia máxima: [250 km v]
```

Estado base:

```txt
Ruta exacta
[ Buscar cerca del origen ] [ Buscar cerca del destino ]
```

## Copy

Título:

> Aeropuertos cercanos

Subtítulo:

> Actívalo si puedes salir o llegar desde otro aeropuerto.

Distancia:

> Distancia máxima

Opciones:

- 100 km
- 250 km
- 500 km
- Personalizar

## QA

- Activar origen cercano.
- Activar destino cercano.
- Activar ambos.
- Cambiar distancia.
- Ver chips.
- Ver query params si aplica.
- Móvil: controles no deben romper línea de forma fea.

## Criterios de aceptación

- Origen/destino cercanos están visibles pero no abruman.
- Radio solo aparece cuando tiene sentido.
- El formulario sigue pareciendo rápido.

---

# Fase 16 — Reordenar formulario principal a versión flexible rápida

## Objetivo

Aplicar el nuevo orden del formulario principal.

## Nuevo orden

1. Origen.
2. Destino.
3. Aeropuertos cercanos.
4. Pasajeros.
5. Fecha.
6. Margen de fecha.
7. Buscar vuelos.
8. Chips compactos.

## Cambios permitidos

- Mover bloques.
- Ajustar grid/responsive.
- Mover margen de fecha junto a fecha.
- Mover vista previa/resumen debajo de CTA.

## Cambios prohibidos

- No mover filtros de resultados si no están listos.
- No meter avanzado en el primer nivel.
- No cambiar API.

## Decisión sobre fecha

La fecha no va “al final absoluto”.
Va como última decisión principal antes de buscar, junto a margen de fecha.

## QA

- Completar búsqueda desde cero.
- Ruta exacta.
- Ruta con cercanos.
- Fecha exacta.
- Fecha ±1 día.
- Pasajeros > 1.
- Móvil.
- Light/dark.
- Tab order.

## Criterios de aceptación

- El formulario se entiende en una pasada.
- La fecha deja de sentirse como ajuste prematuro.
- Buscar queda inmediatamente después de las decisiones principales.
- No se pierde ningún estado.

---

# Fase 17 — Sustituir definitivamente “Ajustes activos” por chips + Más opciones

## Objetivo

Eliminar el bloque grande antiguo del primer nivel.

## Cambios permitidos

- Quitar bloque “Ajustes activos” antiguo del panel principal.
- Dejar chips compactos.
- Dejar “Más opciones” como acceso a avanzados.
- Mantener compatibilidad de estado.

## Cambios prohibidos

- No eliminar funcionalidades.
- No borrar lógica usada por preferencias si sigue necesaria.
- No dejar campos inaccesibles.

## Estado esperado

Primer nivel:

```txt
[Origen] [Destino]
Aeropuertos cercanos...
Pasajeros...
Fecha...
[Buscar vuelos]

Ruta exacta · Fecha exacta · 1 pasajero
[Más opciones]
```

Con flex:

```txt
Cerca del origen · Cerca del destino · Hasta 500 km · ±1 día · 1 pasajero
[Más opciones]
```

## QA

- Confirmar que no aparece el bloque grande.
- Abrir Más opciones y encontrar todos los ajustes avanzados.
- Ver chips en diferentes estados.
- Probar submit.
- Probar URL/query params.
- Probar preferencias aplicadas.

## Criterios de aceptación

- “Ajustes activos” deja de existir como bloque pesado.
- La función de resumen sigue existiendo.
- El usuario medio no ve complejidad innecesaria.
- El usuario avanzado puede seguir configurando.

---

# Fase 18 — Crear rescate contextual cuando no hay resultados

## Objetivo

Convertir “no results” en una ayuda inteligente, no en un callejón sin salida.

## Cambios permitidos

- Añadir módulo de no resultados.
- Ofrecer acciones rápidas:
  - Probar ±1 día.
  - Buscar aeropuertos cercanos.
  - Ampliar al máximo.
  - Abrir más opciones.
- Actualizar estado al pulsar acciones.

## Cambios prohibidos

- No lanzar búsquedas automáticas sin confirmación salvo patrón existente.
- No activar máxima cobertura por defecto.
- No prometer resultados.

## Copy

Título:

> No hay vuelos claros con esta búsqueda

Subtítulo:

> Puedes mantener tu viaje principal y abrir un poco el radar.

Acciones:

- Probar ±1 día.
- Buscar aeropuertos cercanos.
- Ampliar al máximo.
- Más opciones.

Mensaje al activar:

> Listo. Ahora Viru buscará con un poco más de margen.

## Reglas de acción

### Probar ±1 día

- Si fecha exacta, cambia a ±1 día.
- Si ya está ±1 día, ofrece ±2 días.
- Si ya está personalizado, no sobrescribir sin confirmación.

### Buscar aeropuertos cercanos

- Si ninguno activo, activar origen y destino cercanos con radio prudente.
- Si uno activo, activar el otro.
- Si ambos activos, ofrecer ampliar distancia.

### Ampliar al máximo

- Activar ambos cercanos.
- Usar radio alto existente.
- No activar vuelos separados automáticamente salvo decisión explícita del producto.

## QA

- Simular no resultados.
- Pulsar cada acción.
- Verificar cambio de chips.
- Verificar que el usuario puede buscar de nuevo.
- Verificar móvil.
- Verificar dark/light.

## Criterios de aceptación

- Empty state ayuda sin abrumar.
- No aparece panel avanzado entero como castigo.
- Acciones cambian estado de forma clara y reversible.

---

# Fase 19 — Endurecimiento responsive, accesibilidad y estados

## Objetivo

Convertir el rediseño progresivo en UI robusta.

## Cambios permitidos

- Ajustar responsive.
- Mejorar focus.
- Mejorar estados hover/active/disabled.
- Ajustar labels ARIA si hace falta.
- Mejorar validaciones visuales.

## Cambios prohibidos

- No introducir nuevos cambios de producto.
- No mover secciones.
- No rediseñar estética general.

## Checklist responsive

### Desktop

- Formulario no se estira absurdamente.
- Origen/destino tienen prioridad.
- Chips no generan ruido.
- Más opciones no compite con CTA.

### Tablet

- Grid se adapta sin columnas rotas.
- Botón Buscar sigue visible.
- Chips hacen wrap limpio.

### Móvil

- Orden vertical claro.
- Swap origen/destino accesible.
- Aeropuertos cercanos no ocupa media pantalla.
- CTA no queda perdido.
- Modal avanzado usable con dedo.

## Checklist accesibilidad

- Todos los inputs tienen label.
- Chips editables son botones reales.
- Focus visible.
- Modal con escape y foco controlado.
- No se comunica estado solo con color.
- Mensajes de error legibles.

## QA

- Playwright o browser manual.
- Capturas:
  - desktop light;
  - desktop dark;
  - móvil light;
  - móvil dark;
  - Más opciones abierto;
  - no-results.
- Revisar consola.
- Revisar overflow horizontal.

## Criterios de aceptación

- La UI es usable en móvil.
- No hay regresiones visuales graves.
- El flujo se puede completar solo con teclado.
- Dark/light mantienen identidad.

---

# Fase 20 — Limpieza final, documentación y contrato visual

## Objetivo

Cerrar la transición eliminando deuda creada por fases puente.

## Cambios permitidos

- Eliminar componentes legacy no usados.
- Eliminar CSS muerto creado durante fases.
- Actualizar documentación de Quick Search.
- Actualizar tests.
- Añadir notas de producto.
- Añadir changelog si aplica.

## Cambios prohibidos

- No introducir cambios visibles nuevos.
- No refactorizar áreas no relacionadas.
- No cambiar backend.

## Tareas

1. Buscar referencias a:
   - `Ajustes activos` como bloque antiguo.
   - `Cobertura`.
   - `self-connect`.
   - `buffer`.
   - `datos parciales`.
2. Eliminar duplicados.
3. Asegurar que solo queda:
   - chips compactos;
   - Más opciones;
   - filtros post-resultados;
   - rescate no-results.
4. Actualizar tests.
5. Actualizar documentación interna.

## QA final completo

### Funcional

- Ruta exacta.
- Origen cercano.
- Destino cercano.
- Ambos cercanos.
- Radio 100/250/500/personalizado.
- Fecha exacta.
- ±1 día.
- Pasajeros.
- Más opciones:
  - exclusiones;
  - horarios;
  - vuelos separados;
  - información incompleta.
- Resultados:
  - ordenación;
  - precio;
  - duración.
- No resultados:
  - acciones de rescate.

### Visual

- Desktop light.
- Desktop dark.
- Tablet.
- Móvil.
- Modal/acordeón avanzado.
- Empty state.
- Loading.
- Error.

### Técnico

- Typecheck.
- Lint.
- Tests unitarios.
- Tests e2e si existen.
- Sin errores de consola.
- Sin warnings nuevos relevantes.
- Sin overflow horizontal.

## Criterios de aceptación

- La pantalla ya parece “Búsqueda rápida”.
- Los ajustes avanzados siguen existiendo.
- Los filtros de resultados están después de buscar.
- “Ajustes activos” ya no existe como bloque pesado.
- El sistema se entiende sin términos técnicos.
- Viru mantiene personalidad cálida, aeronáutica y cuidada.
- Cada cambio está documentado y verificado.

---

# 3. Tabla resumen de dependencias entre fases

| Fase | Depende de | Puede hacerse sola | Riesgo |
|---:|---|---|---|
| 1 | Ninguna | Sí | Bajo |
| 2 | 1 | Sí | Bajo |
| 3 | 1 | Sí | Bajo |
| 4 | 1 | Sí | Medio |
| 5 | 4 | Sí | Bajo |
| 6 | 5 | Sí | Medio |
| 7 | 6 | Sí | Bajo |
| 8 | 7 | Sí | Medio |
| 9 | 8 | Sí | Medio |
| 10 | 9 | Sí | Medio |
| 11 | 7 | Sí | Medio |
| 12 | 11 | Sí | Medio |
| 13 | 11 | Sí | Medio |
| 14 | 11 | Sí | Medio-alto |
| 15 | 4 | Sí | Medio |
| 16 | 15 | No recomendable sin 15 | Alto |
| 17 | 12-16 | No | Alto |
| 18 | 17 | Sí | Medio |
| 19 | 17-18 | No | Medio |
| 20 | Todas | No | Bajo/medio |

---

# 4. Definition of Done global

Una fase está terminada solo si cumple todo esto:

- El cambio visible corresponde exactamente a la fase.
- No hay cambios de scope.
- La búsqueda sigue funcionando.
- Los estados principales están probados.
- La UI no pierde personalidad Viru.
- Light y dark siguen siendo coherentes.
- Móvil no queda roto.
- No hay textos técnicos prohibidos nuevos.
- No hay errores nuevos de consola.
- Hay commit pequeño y reversible.
- Hay reporte final con evidencia.

---

# 5. Prompt recomendado para dar a Codex en cada fase

Usa este prompt antes de cada fase:

```md
Vas a implementar SOLO la Fase X del documento `plan-20-fases-quick-search-ajustes.md`.

Reglas:
- No ejecutes fases posteriores.
- No hagas rediseños globales.
- No cambies backend ni contratos API.
- No elimines funcionalidad avanzada.
- Mantén personalidad Viru: cálida, premium cercana, aeronáutica, no SaaS genérico.
- Verifica light/dark y móvil si hay cambio visual.
- Haz commit pequeño al final.
- Si detectas que una fase depende de algo no implementado, para y repórtalo.

Entrega:
1. Archivos tocados.
2. Qué cambió.
3. Qué NO cambió.
4. QA ejecutado.
5. Evidencia visual o descripción exacta.
6. Riesgos restantes.
```

---

# 6. Prompt de freno si Codex se empieza a ir de scope

```md
Para. Estás ampliando scope.

Vuelve a la Fase X:
- no implementes fases futuras;
- no refactorices componentes ajenos;
- no cambies layout global;
- no cambies backend;
- no elimines funcionalidades;
- deja el cambio en el mínimo verificable.

Resume qué tocaste y qué revertirías para volver al alcance.
```

---

# 7. Prompt de QA final después de cada fase

```md
Haz QA de la Fase X.

Comprueba:
- `/quick-search` carga sin errores.
- El submit sigue funcionando.
- No hay overflow horizontal.
- El foco es visible.
- Light/dark se ven coherentes.
- Móvil conserva orden lógico.
- No aparecen términos técnicos prohibidos.
- Los ajustes activos/chips reflejan el estado real.
- Si hay filtros movidos, solo aparecen donde corresponde.

Entrega evidencia:
- comandos ejecutados;
- rutas probadas;
- estados probados;
- capturas si aplica;
- errores encontrados;
- si algo no se pudo verificar, dilo.
```

---

# 8. Orden recomendado de revisión humana

Después de cada grupo de fases, revisar manualmente:

## Revisión 1 — después de Fase 3

Pregunta:

> ¿El formulario ya dirige mejor al botón Buscar sin haber cambiado estructura?

## Revisión 2 — después de Fase 6

Pregunta:

> ¿Ajustes activos ya pesa menos mentalmente?

## Revisión 3 — después de Fase 10

Pregunta:

> ¿Los filtros de resultados dejaron de contaminar la búsqueda inicial?

## Revisión 4 — después de Fase 14

Pregunta:

> ¿Los ajustes avanzados siguen accesibles sin molestar?

## Revisión 5 — después de Fase 17

Pregunta:

> ¿Ya podemos decir que “Ajustes activos” fue sustituido bien?

## Revisión 6 — después de Fase 20

Pregunta:

> ¿La pantalla parece búsqueda rápida, pero sigue siendo Viru?

---

# 9. Criterios de rechazo

Rechazar una fase si ocurre cualquiera de estas cosas:

- Aparece una mega-card nueva con todos los ajustes otra vez.
- El CTA Buscar queda más abajo o menos visible.
- Se pierde acceso a exclusiones, horarios o vuelos separados.
- Los filtros de precio/duración siguen antes de buscar al final.
- “Aeropuertos cercanos” queda escondido en avanzado.
- “Máxima cobertura” aparece como opción inicial dominante.
- Hay términos técnicos visibles.
- El modo móvil requiere abrir ajustes para buscar.
- El diseño se vuelve plano, frío o genérico.
- Se cambió backend sin permiso.
- El commit mezcla varias fases.

---

# 10. Resultado final esperado

Al terminar las 20 fases, Quick Search debe sentirse así:

```txt
Búsqueda rápida
Encuentra vuelos en segundos y guarda oportunidades en tu Watchlist.

[Origen]     ⇄     [Destino]

Aeropuertos cercanos
[ Cerca del origen ] [ Cerca del destino ]
Distancia máxima: [250 km]

[Pasajeros] [Fecha]
Margen: [Exacta] [±1 día] [±2 días] [Personalizar]

[Buscar vuelos]

Ruta exacta · Fecha exacta · 1 pasajero
[Más opciones]
```

Si hay resultados:

```txt
Resultados encontrados

Ordenar por: Recomendado
Filtros: Precio · Duración

[Vuelo 1]
[Vuelo 2]
[Vuelo 3]
```

Si no hay resultados:

```txt
No hay vuelos claros con esta búsqueda.
Puedes mantener tu viaje principal y abrir un poco el radar.

[Probar ±1 día]
[Buscar aeropuertos cercanos]
[Ampliar al máximo]
[Más opciones]
```

Y lo más importante:

> El usuario medio nunca tiene que entender ajustes avanzados para buscar.
> El usuario flexible encuentra rápido aeropuertos cercanos.
> El usuario avanzado conserva toda la potencia.
