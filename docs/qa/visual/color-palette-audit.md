Status: canonical
Scope: QA visual
Last reviewed: 2026-05-18
Fuente de verdad: docs/qa/visual/color-palette-audit.md

---

# Auditoria de la paleta de colores y plan de consolidacion

Este documento consolida la paleta visual dual de Viru Tracker para garantizar consistencia entre dark/light bajo una identidad aeronautica calida, con personalidad y claridad operativa.

## 1) Paleta visual consolidada (dual)

| Rol/uso | Dark | Light | Uso recomendado | Contraste de referencia |
|---|---|---|---|---|
| **Lienzo primario** | `#121212` | `#FFFFFF` | Fondo principal por tema | Verificar contraste texto en ambos temas |
| **Panel principal** | `#1E1E1E` | `#F5F5F5` | Paneles y bloques principales | Mantener separacion clara por capas |
| **Superficie secundaria** | `#242424` | `#F0F0F0` | Tarjetas internas y subpaneles | Evitar planos sin jerarquia |
| **Texto principal** | `#F5EAD6` | `#121212` | Lectura principal por tema | Cumplir AA en ambos temas |
| **Accent primario** | `#FFB000` | `#FFB000` | CTA y acciones clave | Compartido entre temas |
| **Accent secundario** | `#10B981` | `#10B981` | Estados secundarios / radar | Compartido entre temas |
| **Info/altitud** | `#50BFE6` | `#50BFE6` | Informacion y data visual | Compartido entre temas |
| **Error/alerta** | `#FF6464` | `#FF6464` | Error y advertencia critica | Compartido entre temas |
| **Ambiente/haze** | `#7C7CFF` | `#7C7CFF` | Solo detalle atmosferico | No usar como color masivo |

> **Notas**
> - La paleta es unica y coherente entre temas; cambia luminancia, no personalidad.
> - Se prohiben colores fuera de esta paleta salvo validacion explicita.
> - En light mode, evitar resultado "SaaS blanco plano": conservar jerarquia, calidez y cues de vuelo.
> - En dark mode, evitar resultado lugubre: mantener contraste, profundidad y legibilidad humana.
> - Cualquier resultado sobrio/frio/contenido es inconsistente con la direccion visual vigente.

## 2) Plan de consolidacion
1. Auditar estilos para detectar colores fuera de paleta.
2. Sustituir hardcodes por tokens/variables semanticas.
3. Mantener trazabilidad en QA por componente y por tema.
4. Validar contraste y foco visible en dark y light.
5. Registrar resultados en la matriz de QA.

## 3) Checklist QA de color
- Cohesion cromatica: sin colores fuera de paleta.
- Consistencia semantica: estados compartidos entre temas.
- Contraste validado: textos e iconos cumplen AA en dark y light.
- Jerarquia visual: paneles/superficies conservan estructura en ambos temas.
- Calidez visual: el resultado no debe sentirse frio, plano o corporativo.
- Uso de `#7C7CFF`: solo ambiental/haze, nunca color dominante de interfaz.
