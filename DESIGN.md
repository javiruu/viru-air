# DESIGN.md — Viru Tracker (Dirección de Diseño)

**Estado:** Vivo  
**Última revisión:** 2026-05-15  
**Área:** Diseño (UI/UX)

## 1) Principios de marca y tono
- **No es SaaS genérico:** Viru Tracker es un producto aeronáutico sofisticado, no un dashboard genérico.  
- **Tono Dark-Luxe:** Interfaz nocturna y cinematográfica; sensación premium y editorial. Evoca centros de control o cabinas iluminadas tenuemente.  
- **Claridad y confianza:** Las pantallas deben ser claras y controladas, con jerarquía visual fuerte, espaciados amplios y densidad de información útil.  
- **Mejoras incrementales:** Favorecer iteraciones progresivas en lugar de rediseños radicales.

## 2) Paleta y tokens canónicos
**Paleta base alineada a UI:**  
- Fondo del lienzo: #121212 (navy oscuro).  
- Superficie primaria: #1E1E1E (panel principal).  
- Superficie secundaria: #242424 (tarjetas/paneles internos).  
- Texto principal: #F5EAD6 (crema cálida para legibilidad).  
- Acento primario (`--accent`): #FFB000 (ámbar – acciones importantes).  
- Acento secundario (`--accent-2`): #10B981 (verde–estados/adicionales).  
- Bordes (`--border`): #242424 (gris oscuro).  
- Sombras (`--shadow`): negra translúcida suave.  

**Reglas:**  
- **Consistencia cromática:** usar únicamente colores de la paleta definida (no saturados extra).  
- **Evitar saturación:** no fondos de colores vivos ni sombras intensas.  
- **Modos Dark/Light:** asegurar contraste legible en ambos. (En Dark usar fondos gris oscuro, en Light adaptar inversamente según paleta).

## 3) Tipografía y microcopy
- **Titulares:** Playfair Display (estilo clásico/editorial).  
- **Subtítulos/cuerpo:** IBM Plex Sans.  
- **Datos de vuelo:** Fuente monoespaciada (ej. para códigos de aeropuertos, horarios) para evocar estilo técnico.  
- **Lenguaje:** mantener glosario en español (Panel, Seguimiento, Búsqueda rápida, Alerta, Histórico, Comparativa, Preferencias, Ayuda, Vuelo, Terminal).  
- **Redacción:** mensajes breves, claros, accionables. Nunca mezclar ES/EN en UI visible.  

## 4) Layout, espaciamiento y composición
- **Cabeceras:** Botón Atrás + Título + Subtítulo + acciones alineadas (stack horizontal).  
- **Paneles:** Borde fino y radio consistente (#242424), sombra muy suave (elev. 1). Evitar fondos lisos sin textura o gradiente leve.  
- **Separación:** preferir espacios generosos (márgenes/paddings) a divisores duros.  
- **Diseño asimétrico controlado:** Asimetría leve si mejora legibilidad o sensación “editorial”.  

## 5) Componentes congelados (UI System v1)
Patrones base (`components.css`):  
`panel`, `panel-soft`, `page-header`, `panel-header`, `panel-actions`,  
`panel-title`, `panel-subtitle`, `list-row`, `action-row`, `row-actions`,  
`section-gap` (sm/lg/), `status-pill`, `state-success|warning|error|info`.  

*Regla de extensión:* si un patrón se repite en 2+ pantallas, crear componente genérico/token.  

## 6) Estados y semántica
Única semántica:  
- `success`: éxito/completado.  
- `warning`: parcial/pendiente.  
- `error`: falla.  
- `info`: neutro/informativo.  

*Nota:* se abandona el término `warn` (usar `warning`).  

## 7) Interacción y microanimación
- **Entrada de secciones:** fade-in con desplazamiento suave 4–8px.  
- **Cambio de filtros (tabs, selects):** transiciones 80–120ms.  
- **Hover de tarjetas:** elevar 1px + glow tenue #FFB000 (como luz de pista).  
- **Click en botones:** compresión de 1–2px.  
- **Uso de motion:** solo para clarificar estados/continuidad, nunca puramente decorativo.  

## 8) QA visual mínimo
Antes de publicar cambios de UI:  
- Validar flujos clave (e.g. `/dashboard`, `/watchlist`, `/quick-search`, `/alerts`, `/login`, `/register`).  
- Probar en Desktop/Tablet/Móvil (p.ej. 1440x900, 768x1024, 375x812, 320x780).  
- Confirmar no overflow horizontal, no elementos solapados, focus visible, CTA principal claro.  
- Revisar estados clave: cargando, vacío, error, éxito (y cualquier animación/placeholder).  

## 9) Límites para desarrolladores
- Cambios visuales deben ser incrementales y bien documentados.  
- **No** modificar lógica de negocio, rutas o API sin aprobación.  
- **No** añadir librerías solo para ajustes estéticos menores.  
- Seguir consistencia con `AGENTS.md` y documentación UI oficial.  

## 10) Skill de diseño incremental
- Skill: `/.codex/skills/taste-skill/SKILL.md`.  
- Su uso es para guiar jerarquía, ritmo, composición, motion y pulido visual.  
- **Prioridad:** este documento y los docs en `docs/ui/` son la fuente definitiva para UI/estética.
