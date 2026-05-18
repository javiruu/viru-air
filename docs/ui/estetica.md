Status: canonical
Scope: Sistema de diseño UI, contrato visual, guía de estilo
Last reviewed: 2026-05-18
Fuente de verdad: docs/ui/estetica.md

---

# Dirección Visual: «Aviation Dark-Luxe / Daylight Flight Intelligence»

**Viru Tracker** adopta una estética dual: **Dark-Luxe** en modo nocturno y una **contraparte luminosa en modo día**. Ambos temas comparten la misma identidad aeronáutica, editorial y premium: códigos IATA, rutas estilizadas, luces de pista, terminales y lenguaje de flight intelligence.

## Principios de Estilo
- **Oscuridad Premium (modo nocturno):** canvas `#121212`, paneles `#1E1E1E/#242424`, texto principal `#F5EAD6`.
- **Claridad Diurna (modo claro):** canvas `#FFFFFF`, paneles `#F5F5F5/#FAFAFA/#F0F0F0`, texto principal `#121212`.
- **Acentos compartidos:** `#FFB000` (pista/acción), `#10B981` (radar/estado), `#50BFE6` (info/altitud), `#FF6464` (alerta/error).
- **Personalidad consistente:** dark y light cambian luminancia, no identidad; evitar look SaaS genérico en modo claro.
- **Tipografía editorial:** titulares en Playfair Display y cuerpo en IBM Plex Sans; monoespaciada para datos de vuelo cuando aplique.
- **Jerarquía y ritmo:** contraste claro entre niveles de información, espacios amplios y agrupación fuerte.
- **Microanimación sobria:** fade + desplazamiento corto, elevación mínima y feedback claro de interacción.

## Esquema de Componentes
- **Cabecera (`page-header`):** mismo patrón en ambos temas; cambian superficies/contraste, no estructura.
- **Paneles (`panel`, `panel-soft`):**
  - Dark: `#1E1E1E` / `#242424`
  - Light: `#F5F5F5` / `#FAFAFA` o `#F0F0F0`
- **Tarjetas (`card`, `result-row`):** profundidad sutil en dark y separación limpia en light, con cues de vuelo consistentes.
- **Inputs/Form:** foco visible en ambos temas; halo y estados semánticos coherentes.
- **Botones:** semántica y prioridad idénticas en dark/light; acento primario compartido `#FFB000`.
- **Overlays/Modales:** mantener legibilidad y jerarquía en ambos modos, sin sombras agresivas ni planos vacíos.

## Checklist QA Visual (previo a merge)
- Paleta consistente en ambos temas; sin colores fuera de sistema.
- Contraste mínimo AA en dark y light para texto, iconos y controles.
- Cues aeronáuticos presentes donde corresponda (IATA, rutas, terminales, radar/altitud).
- Misma jerarquía visual y semántica de estados en dark/light.
- Tipografía, spacing y componentes sin desalineaciones entre temas.
- Animaciones sobrias y funcionales en ambos modos.
