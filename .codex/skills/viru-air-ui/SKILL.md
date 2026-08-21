---
name: Viru Air UI
description: Mejoras incrementales de UI/UX para Viru Air con identidad calida, animada, cercana y no generica.
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

# Skill: Viru Air UI

## Objetivo
Aplicar mejoras visuales incrementales y verificables en Viru Air, siguiendo el contrato creativo y visual único de `DESIGN.md`.

## Lectura obligatoria

Antes de diseñar, proponer o implementar cualquier cambio UI/UX, la única lectura obligatoria de diseño es `DESIGN.md`. Ese documento contiene la identidad, los límites técnicos, la libertad creativa, la accesibilidad y el QA visual de Viru. Las especificaciones funcionales aplicables conservan su autoridad sobre flujo, datos y contratos.

## Fuera de alcance por defecto
- Cambiar logica de negocio.
- Alterar rutas o contratos API.
- Reescribir pantallas completas sin solicitud explicita.
- Introducir dependencias nuevas para ajustes visuales menores.

## Flujo recomendado
1. Leer `DESIGN.md`.
2. Identificar un unico problema de jerarquia/lectura/interaccion.
3. Proponer y aplicar el cambio minimo viable.
4. Verificar con evidencia visual y checks de estado afectados.
