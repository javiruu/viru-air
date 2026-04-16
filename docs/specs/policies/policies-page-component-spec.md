Status: canonical
Scope: active product, UI, or policy specification
Last reviewed: 2026-04-15
Canonical source: docs/specs/policies/policies-page-component-spec.md
Related: docs/specs/README.md, docs/INDICE_UNICO.md

---
# Especificacion de componentes — Politicas y Transparencia (Viru)

## 1) Hero de confianza
- Elementos:
  - H1: “Politicas y Transparencia”
  - Subtitulo de una linea
  - Metadatos: Ultima actualizacion, Version, Idioma, Tiempo de lectura
  - Acciones: “Atras” y “Volver al panel”
- Comportamiento:
  - Mantener jerarquia H1 y lectura clara
  - Metadatos visibles y escaneables
- Accesibilidad:
  - H1 unico
  - Links con focus visible

## 2) Resumen ejecutivo (TL;DR)
- Caja destacada con 6–8 bullets
- Uso de badge “Transparencia”
- Texto en lenguaje llano

## 3) Indice navegable (sticky / collapsable)
- Navegacion con anchors internos
- Estado activo por scroll
- Desktop: visible siempre
- Movil: colapsable con toggle “Abrir indice”
- Accesibilidad:
  - nav con `aria-label`
  - botones con `aria-expanded`

## 4) Cuerpo de politicas completo
Secciones largas A–M:
- A) Uso responsable
- B) Alcance del servicio y limites
- C) Datos de proveedor y calidad del dato
- D) Alertas, recomendaciones y predicciones
- E) Privacidad y proteccion de datos
- F) Conservacion, borrado y portabilidad
- G) Seguridad de cuenta y sesiones
- H) Cookies, analitica y telemetria
- I) Consejos y politicas por pais
- J) Deep-link y terceros
- K) Exencion de responsabilidad y no asesoramiento financiero
- L) Cambios de politica y control de versiones
- M) Contacto legal / soporte privacidad

Componentes comunes:
- Encabezado con H2 + badge semantico
- Parrafos con lectura por capas
- Lista simple (sin jerga)
- Tabla de flujo para borrado

## 5) Bloque “Tus derechos, en simple”
- Formato acordeon con `<details>`
- Items:
  - Acceso
  - Rectificacion
  - Eliminacion
  - Limitacion/oposicion
  - Portabilidad
  - Retirada de consentimiento

## 6) FAQ amigable
- Minimo 12 preguntas
- Formato acordeon `<details>`
- Respuestas breves, directas

## 7) CTA final de confianza
- Botones:
  - Volver al panel
  - Contactar soporte
  - Solicitar eliminacion de datos
- Disposicion flexible y responsiva

## 8) Resumen rapido fijo
- Aside sticky en desktop
- Caja con 4–6 bullets
- Se mantiene visible mientras se lee

## 9) Floating CTA (movil)
- Botones “Subir” e “Indice”
- Posicion fixed, bottom-right

## 10) Badges semanticos
- “Importante”
- “Transparencia”
- “Limitacion”
- “Tu control”

## 11) Accesibilidad
- H1–H3 en orden
- Focus visible
- Contraste AA minimo
- Navegacion por teclado
- Landmarks y `aria-label` donde aplique






