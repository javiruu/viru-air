Status: canonical  
Scope: Sistema de diseño UI, contrato visual, guía de estilo  
Last reviewed: 2026-05-15  
Fuente de verdad: docs/ui/estetica.md  

---  

# Dirección Visual: «Aviation Dark-Luxe»  

**Viru Tracker** adopta una estética nocturna, cinematográfica y premium inspirada en la aviación. La interfaz debe evocar la elegancia de un centro de control de vuelos: fondo oscuro profundo (azul noche casi negro), toques cálidos (ámbar y crema) y detalles sutiles de aeropuertos. Se incorporan elementos alusivos al vuelo (códigos IATA, rutas de avión, luces de pista).  

## Principios de Estilo  
- **Oscuridad Premium:** Base #121212 (casi negro) para el lienzo; superficies diferenciadas en #1E1E1E o #242424. Evitar negro puro (#000) por permitir capas sutiles.  
- **Matices Cálidos:** Detalles en ámbar (#FFB000, luz de pista) y crema cálida (#F5EAD6) para resaltar elementos clave. Inspirado en paletas de alta tecnología audiovisuales.  
- **Tono Técnico:** Toques de verde radar (#10B981) e “hielo celeste” (#50BFE6) para semántica secundarias (status, gráficas). Evitar colores vivos no acordes; mantener coherencia fría y sobria.  
- **Referencias Aéreas:** Etiquetas tipo cárteles de aeropuerto (códigos 3 letras para aeropuertos, terminales), iconografía geométrica (aviones estilizados, rutas) y animaciones de trayectos. Por ejemplo, “Ruta viva”: una línea punteada animada con un avión en transición.  
- **Tipografía Editorial:** Titulares en Playfair Display (serif elegante) y cuerpo en IBM Plex Sans (moderna). Datos de vuelo (códigos, horarios) pueden usar monoespaciado (evoca pasarela de abordaje).  
- **Jerarquía Clara:** Contraste marcado entre título/subtítulo y cuerpo; sparrings de line-height aireados. Espaciados amplios en listas y secciones (evitar divisores duros).  
- **Iluminación Ambiental:** Fondos con micro-gradientes o texturas muy sutiles (niebla ligera, traza de rutas) para simular atmósfera editorial, en lugar de colores planos.  
- **Microanimaciones Sutiles:** Transiciones suaves (“fade + deslizar 4–8px” al mostrar secciones), elevación mínima (1px) y brillo tenue en hover, compresión leve al hacer click. Estas animaciones ilustran cambios de estado sin distraer.  
- **Reglas de Contraste:** Siempre texto claro sobre fondo oscuro (relación >= 15:1 en modo nocturno). Íconos y etiquetas aumentan su brillo en modo oscuro. Evitar sombras muy pronunciadas o fondos saturados.  

## Esquema de Componentes  
- **Cabecera de página (page-header):** Siempre botón Atras, título y subtítulo (alineación izquierda) y acciones a la derecha. Título en Playfair Display, subtítulo en IBM Plex Sans.  
- **Paneles:** Base en `.panel` con fondo #1E1E1E, bordes finos #242424 y sombras muy suaves. Paneles secundarios con `.panel-soft` usando fondo más claro #242424.  
- **Tarjetas Analíticas:** Tarjetas de datos (`.card` o `.result-row`) con halos tenues de luz y elevación al hacer hover (1px + glow). Colocar iconos lineales (delgadas) para categorías.  
- **Inputs y Formulario:** Labels e instrucciones en crema cálida, inputs con halo adaptativo azul claro. Estados: foco con glow ámbar suave, validación con borde verde tenue.  
- **Listas y Resultados:** Separación generosa (padding amplio) en filas. Metadatos en un tono gris claro (#A0A0A0) para jerarquía secundaria. Indicadores de estado (`.status-pill`) en color semántico (verde, ámbar, coral).  
- **Botones:** Botón primario con doble capa (fondo principal + glow ámbar tenue detrás). Al presionar, ápice comprimido. Botones secundarios/ghost en tonos neutros (texto crema sobre #1E1E1E).  
- **Modales y Overlays:** Fondo modal negro con opacidad (#121212 a 85%). Tarjetas modales en #1E1E1E, sin sombras duras. Botón de cierre claro contrastante.  

## Checklist QA Visual (previo a merge)  
- **Tonos de color:** No usar colores ajenos a la paleta (sólo #121212,#1E1E1E,#F5EAD6,#FFB000,#10B981,#50BFE6,#FF6464,#7C7CFF).  
- **Contraste:** Verificar contraste de texto mínimo 4.5:1 con fondos (p.ej. crema vs #121212, ámbar vs #1E1E1E).  
- **Iconografía:** Confirmar que iconos de vuelo (avión, radar) estén alineados con el estilo lineal sobrio.  
- **Animaciones:** Asegurar uso de transiciones suaves definidas (ver sección Microanimaciones); evitar cualquier movimiento excesivo.  
- **Consistencia:** Revisar coherencia tipográfica y de espaciados en todos los ejemplos de pantalla (misma fuente/gap en títulos, botones, inputs).  
- **Referencias de marca:** Verificar presencia de al menos un “cue” aeronáutico (código de aeropuerto, ruta de vuelo, etc.) en pantallas contextuales (si aplica).
