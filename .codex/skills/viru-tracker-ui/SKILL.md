---
name: Viru Tracker UI
description: Mejoras incrementales de UI/UX para Viru Tracker con identidad calida, animada, cercana y no generica.
trigger_words:
  - diseno
  - interfaz
  - visual
  - ui
  - viru
od:
  mode: prototype
  platform: desktop
  scenario: design
  preview:
    type: html
    entry: index.html
  design_system:
    requires: true
  example_prompt: "Describe la jerarquia visual actual de una ruta y propone un unico ajuste incremental sin cambiar logica ni rutas."
---

# Skill: Viru Tracker UI

## Objetivo
Aplicar mejoras visuales incrementales y verificables en Viru Tracker, preservando su identidad calida, con personalidad y su contrato UI canonico.

## Alcance obligatorio
- Cambios incrementales UI/UX en superficies existentes.
- Mantener paleta/tokens y semantica de estados (`success`, `warning`, `error`, `info`).
- Respetar componentes y patrones base del sistema UI vigente.
- Favorecer claridad + calidez + personalidad sin ruido visual.
- Reforzar microinteracciones suaves y microcopy vivo cuando aporte comprension.

## Fuera de alcance por defecto
- Cambiar logica de negocio.
- Alterar rutas o contratos API.
- Reescribir pantallas completas sin solicitud explicita.
- Introducir dependencias nuevas para ajustes visuales menores.

## Guardrails de interpretacion
- No entregar propuestas sobrias, frias, contenidas o corporativas como salida valida.
- No usar "editorial premium" como direccion dominante.
- No confundir simplicidad con austeridad ni con perdida de alma visual.

## Flujo recomendado
1. Leer `DESIGN.md` y referencias de esta skill.
2. Identificar un unico problema de jerarquia/lectura/interaccion.
3. Proponer y aplicar el cambio minimo viable.
4. Verificar con evidencia visual y checks de estado afectados.

## Referencias locales
- `references/product-context.md`
- `references/visual-direction.md`
- `references/qa-checklist.md`
