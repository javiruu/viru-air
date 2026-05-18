Status: canonical
Scope: QA visual
Last reviewed: 2026-05-18
Fuente de verdad: docs/qa/visual/color-palette-audit.md

---

# Auditoría de la paleta de colores y plan de consolidación

Este documento consolida la paleta visual dual de Viru Tracker para garantizar consistencia entre los temas dark/light bajo la misma identidad aeronáutica.

## 1) Paleta visual consolidada (dual)

| Rol/uso | Dark | Light | Uso recomendado | Contraste de referencia |
|---|---|---|---|---|
| **Lienzo primario** | `#121212` | `#FFFFFF` | Fondo principal por tema | Verificar contraste texto en ambos temas |
| **Panel principal** | `#1E1E1E` | `#F5F5F5` | Paneles y bloques principales | Mantener separación clara por capas |
| **Superficie secundaria** | `#242424` | `#F0F0F0` | Tarjetas internas y subpaneles | Evitar planos sin jerarquía |
| **Texto principal** | `#F5EAD6` | `#121212` | Lectura principal por tema | Cumplir AA en ambos temas |
| **Accent primario** | `#FFB000` | `#FFB000` | CTA y acciones clave | Compartido entre temas |
| **Accent secundario** | `#10B981` | `#10B981` | Estados secundarios / radar | Compartido entre temas |
| **Info/altitud** | `#50BFE6` | `#50BFE6` | Información y data visual | Compartido entre temas |
| **Error/alerta** | `#FF6464` | `#FF6464` | Error y advertencia crítica | Compartido entre temas |
| **Ambiente/haze** | `#7C7CFF` | `#7C7CFF` | Solo detalle atmosférico | No usar como color masivo |

> **Notas**
> - La paleta es única y coherente entre temas; cambia luminancia, no personalidad.
> - Se prohíben colores fuera de esta paleta salvo validación explícita.
> - En light mode, evitar resultado “SaaS blanco plano”: conservar jerarquía editorial y cues de vuelo.

## 2) Plan de consolidación
1. Auditar estilos para detectar colores fuera de paleta.
2. Sustituir hardcodes por tokens/variables semánticas.
3. Mantener trazabilidad en QA por componente y por tema.
4. Validar contraste y foco visible en dark y light.
5. Registrar resultados en la matriz de QA.

## 3) Checklist QA de color
- Cohesión cromática: sin colores fuera de paleta.
- Consistencia semántica: estados compartidos entre temas.
- Contraste validado: textos e iconos cumplen AA en dark y light.
- Jerarquía visual: paneles/superficies conservan estructura en ambos temas.
- Uso de `#7C7CFF`: solo ambiental/haze, nunca color dominante de interfaz.
