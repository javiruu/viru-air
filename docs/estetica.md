# Guia de Estetica Viru

OBJETIVO
========
Estandarizar la identidad visual del producto y aportar ideas de evolucion sin romper la estetica editorial.

ESTRUCTURA ESTANDAR DE SECCIONES
================================
- Cabecera: boton Atras, titulo, subtitulo y acciones.
- Panel: borde fino, radio consistente y sombra suave.
- Bloques internos: glass leve o superficie secundaria.
- Inputs: borde suave, halo adaptativo y feedback inmediato.
- Listas: separacion por aire, no por lineas duras.
- Boton principal: doble capa con glow tenue y micro-presion.

TOKENS PRINCIPALES
==================
- `--bg`: base del lienzo.
- `--surface`: panel principal.
- `--surface-2`: subpanel o tarjeta.
- `--ink`: texto principal.
- `--accent`: accion principal.
- `--accent-2`: estado o secundaria.
- `--border`: linea sutil.
- `--shadow`: profundidad suave.

MATRIZ DE COMPONENTES
=====================
- Panel base: `.panel`.
- Panel suave: `.panel.panel-soft`.
- Stack y spacing: `.stack`, `.stack-lg`, `.section-gap`, `.section-gap-sm`, `.section-gap-lg`.
- Acciones: `.row-actions`, `.btn-primary`, `.btn-ghost`.
- Estados: `.notice`, `.notice-success`, `.notice-error`.
- Empty state: ghost grid + texto tenue.
- Resultados: `.result-row`, `.result-actions`, `.result-meta`, `.result-source`.
- Leyendas: `.legend-chip`, `.legend-dot`.

IDEAS INNOVADORAS, PERO SOBRIAS
===============================
- Focus Lens: microhalo que se ajusta al color semantico del campo.
- Ruta viva: linea de trayecto con avion en transicion corta.
- Ghost Grid: grid tenue en areas sin datos para evitar vacio.
- Calendario latente: placeholder fantasma que sugiere el ritmo.
- Scrollbar contextual: ancho reducido y opacidad variable.
- Confirmacion silenciosa: borde suave verde cuando el formulario esta listo.
- Microresumen: tarjeta flotante con sintesis previa al submit.
- Tarjeta ambiental: glow inferior sutil para elevar el formulario sin ruido.
- Mapa fantasma: textura de rutas muy tenue en paneles de busqueda.

REGLAS DE CONTRASTE
===================
- Texto principal siempre sobre superficie clara en modo dia.
- En modo noche, subir contraste de iconos y labels.
- Evitar fondos saturados y sombras oscuras agresivas.

MICRO-ANIMACIONES
=================
- Entrada de bloques: fade + desplazamiento 4 a 8px.
- Cambios de filtro: 80 a 120ms.
- Hover de tarjeta: 1px de elevacion y glow tenue.
- Press de boton: 1 a 2px de compresion.

CONTROL DE VARIACION ENTRE APARTADOS
====================================
- Tipografia constante en titulos y subtitulos.
- Mismo sistema de radios y bordes.
- Estilo coherente en botones y inputs.
- Fondo con microgradiente, no fondos planos distintos por pagina.

CHECKLIST DE CALIDAD VISUAL
===========================
- No hay colores fuera de paleta base.
- No hay sombras fuertes ni neomorfismo excesivo.
- Empty states no se ven vacios.
- Los datos criticos destacan sin ruido.

RUTA DE EVOLUCION
=================
- Componentes base reutilizables para cards analiticas.
- Tokens de estado extendidos (sin datos, degradado, sincronizando).
- Iconografia lineal consistente en cabeceras y filtros.

ESTANDARES POR COMPONENTE
=========================
Cabeceras (page-header)
- Siempre: boton Atras, titulo, subtitulo, acciones a la derecha.
- Titulos con Playfair Display y subtitulo en IBM Plex Sans.
- Acciones alineadas con `page-actions` y gap consistente.

Paneles
- `panel` como base, `panel-soft` para subpaneles o contexto secundario.
- Usar `panel-title` y `panel-subtitle` en headers internos.
- Evitar fondos planos sin gradiente o textura sutil.

Formularios
- Labels con clase `field` y hint opcional (`.hint`).
- Inputs con halo adaptativo; evitar estilos inline.
- Campos date usan `date-field` para consistencia.

Listas y resultados
- Estructura con `list-row` o `result-row` para alineacion y separacion suave.
- Metadatos con `result-meta` y fuentes con `result-source`.

Modales
- Header con titulo + subtitulo, boton de cierre claro.
- Contenedor `modal-card` y overlay `modal-overlay` sin sombras agresivas.

Estados y mensajes
- `notice` para mensajes y variantes `notice-success` / `notice-error`.
- Separar con `section-gap` para no romper ritmo vertical.

Graficos y calendario
- Placeholder ghost en ausencia de datos.
- Leyendas con `legend-chip` y punto `legend-dot`.
