Status: canonical
Scope: Sistema de diseno UI, contrato visual, guia de estilo
Last reviewed: 2026-05-18
Fuente de verdad: docs/ui/estetica.md

---

# Direccion Visual: "Aviation Warm-Luxe / Daylight Flight Soul"

**Viru Tracker** adopta una estetica dual: **Dark-Luxe cinematografico** en modo nocturno y una **contraparte luminosa con alma** en modo dia. Ambos temas comparten identidad aeronautica, personalidad visual y calidez premium: codigos IATA, rutas estilizadas, luces de pista, terminales y lenguaje de flight intelligence.

## Principios de estilo
- **Dark cinematografico (modo nocturno):** canvas `#121212`, paneles `#1E1E1E/#242424`, texto principal `#F5EAD6`.
- **Light con caracter (modo claro):** canvas `#FFFFFF`, paneles `#F5F5F5/#FAFAFA/#F0F0F0`, texto principal `#121212`.
- **Acentos compartidos:** `#FFB000` (pista/accion), `#10B981` (radar/estado), `#50BFE6` (info/altitud), `#FF6464` (alerta/error).
- **Personalidad consistente:** dark y light cambian luminancia, no identidad; evitar look SaaS blanco generico.
- **Tipografia con gusto:** titulares en Playfair Display y cuerpo en IBM Plex Sans; monoespaciada para datos de vuelo cuando aplique.
- **Jerarquia y ritmo:** contraste claro entre niveles de informacion, agrupacion fuerte y composicion con intencion.
- **Motion con intencion:** claridad + delight + continuidad + personalidad, con transiciones suaves y controladas.

## Anti-anclas (lectura obligatoria)
- "Claro" no significa austero.
- "Premium" no significa distante.
- "Limpio" no significa frio ni contenido.
- "Ordenado" no significa editorial serio.
- "Funcional" no significa dashboard corporativo.

## Reglas visuales concretas
- Anadir microinteracciones en hover, seleccion, carga, empty states y confirmaciones.
- Usar microcopy humano y cercano, sin tono infantil.
- Reforzar detalles aeronauticos sutiles: rutas, codigos IATA, logica tipo boarding pass, runway lights, radar, terminal glass.
- Dar personalidad a estados vacios, loading y exito.
- Evitar grids repetitivas de cards sin ritmo y evitar estetica dominante de "dashboard serio".
- Mantener contraste, accesibilidad y claridad en ambos temas.

## Esquema de componentes
- **Cabecera (`page-header`):** mismo patron en ambos temas; cambian superficies/contraste, no estructura.
- **Paneles (`panel`, `panel-soft`):**
  - Dark: `#1E1E1E` / `#242424`
  - Light: `#F5F5F5` / `#FAFAFA` o `#F0F0F0`
- **Tarjetas (`card`, `result-row`):** profundidad sutil en dark y separacion limpia en light, con cues de vuelo consistentes.
- **Inputs/Form:** foco visible en ambos temas; halo y estados semanticos coherentes.
- **Botones:** semantica y prioridad identicas en dark/light; acento primario compartido `#FFB000`.
- **Overlays/Modales:** mantener legibilidad y jerarquia en ambos modos, sin sombras agresivas ni planos vacios.

## Checklist QA visual (previo a merge)
- Paleta consistente en ambos temas; sin colores fuera de sistema.
- Contraste minimo AA en dark y light para texto, iconos y controles.
- Cues aeronauticos presentes donde corresponda (IATA, rutas, terminales, radar/altitud).
- Misma jerarquia visual y semantica de estados en dark/light.
- Tipografia, spacing y componentes sin desalineaciones entre temas.
- Animaciones suaves y funcionales que aporten claridad, delight y continuidad.
- El resultado final no puede percibirse como sobrio, frio o corporativo como tono dominante.
