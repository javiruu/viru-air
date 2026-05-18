Status: canonical  
Scope: QA visual  
Last reviewed: 2026-05-15  
Fuente de verdad: docs/qa/visual/color-palette-audit.md  

---  

# Auditoría de la paleta de colores y plan de consolidación

Este documento consolida la **paleta definitiva** de Viru Tracker bajo la nueva dirección “Aviation Dark-Luxe” y detalla el plan de migración desde colores dispersos. Debe usarse como referencia para asegurar consistencia cromática en todo el producto.

## 1) Paleta visual consolidada

| Rol/uso                   | Color (HEX)  | Contraste (fondo oscuro/base) | Uso recomendado                                      |
|---------------------------|-------------|-------------------------------|------------------------------------------------------|
| **Fondo primario**        | `#121212`   | 17.6:1 (vs crema)             | Fondo principal (mode noche, *canvas* general)       |
| **Panel principal**       | `#1E1E1E`   | 15.7:1                         | Paneles de UI principales, secciones destacadas      |
| **Superficie secundaria** | `#242424`   | 14.5:1                         | Tarjetas internas, modales, overlays oscuros         |
| **Texto principal**       | `#F5EAD6`   | 17.6:1                         | Titulos y texto por defecto sobre fondo oscuro       |
| **Texto secundario**      | `#CCCCCC`   | 10.2:1                         | Subtítulos, etiquetas, leyendas secundarias          |
| **Accent primario**       | `#FFB000`   | 10.2:1                         | CTA principal, íconos de acción destacada (ámbar)    |
| **Accent secundario**     | `#10B981`   | 7.4:1                          | Estados secundarios, gráficos informativos (verde)   |
| **Info/altitud**         | `#50BFE6`   | 8.9:1                          | Gráficos/claves informativas (azul claro)            |
| **Advertencia/alerta**    | `#FF6464`   | 6.5:1                          | Mensajes de error/alerta (coral)                     |
| **Ambiente (humo)**       | `#7C7CFF`   | 5.5:1                          | Detalles atmosféricos suaves, gradientes ligeros     |

> **Notas:** 
> - Todos los colores sobre fondo (#121212 o #1E1E1E) cumplen contraste WCAG AA/AAA.  
> - Se prohíben colores no listados (verde neón, magenta, amarillo puro, etc.).  
> - Los neutrales (borde, sombra) usarán variantes de los anteriores (p.ej. bordes `#242424`, sombras negras translúcidas).  

## 2) Plan de consolidación
1. **Identificar paleta actual:** Auditar estilos CSS para detectar colores fuera de la paleta base.  
2. **Reemplazar colores:** Sustituir instancias directas (hex en CSS/JSX) por tokens o variables alineadas (ej. `--accent`, `--ink`).  
3. **Actualizar tokens:** Asegurar que `tokens.css` y `design tokens` reflejen la paleta arriba.  
4. **Verificación accesibilidad:** Con cada cambio, comprobar contraste con herramienta (>=4.5:1).  
5. **Documentación QA:** Registrar resultados en la matriz de trazabilidad QA y revisar en PR correspondiente.  

## 3) Checklist QA de color
- **Cohesión cromática:** Ningún elemento UI usa color fuera de la paleta definida.  
- **Consistencia con tokens:** Todos los colores aplicados provienen de los tokens canónicos.  
- **Contraste validado:** Texto/íconos sobre cada color de fondo cumplen con AA (p.ej. 15:1 para texto primario).  
- **Diseño visual:** Los estados (success/warning/error) utilizan los tonos semánticos correctos (verde, ámbar, coral).  
- **Actualización completa:** No quedan referencias a colores antiguos (e.g. eliminar `#ff0000`, `#00ff00` directos en hojas de estilo).
