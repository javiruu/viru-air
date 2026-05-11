# Guía corta de microcopy base (Ciclo 1)

## Objetivo
Unificar lenguaje visible de interfaz en español para acciones comunes y estados globales.

## 1) Acciones (botones/links)
- Usar verbos directos y cortos:
  - **Guardar**
  - **Cancelar**
  - **Volver**
  - **Actualizar**
  - **Eliminar**
  - **Reintentar**
- Evitar mezclar variantes en la misma pantalla (`Guardar cambios` vs `Guardar`) salvo contexto claro.

## 2) Estados de carga
- Formato recomendado: `Cargando…`
- Si aplica contexto: `Cargando resultados…`, `Cargando historial…`
- No usar mensajes largos en spinners.

## 3) Estados vacíos (empty)
- Estructura recomendada:
  1. Título corto: `Aún no hay datos`
  2. Explicación breve: `Añade un vuelo para empezar.`
  3. CTA único: `Añadir vuelo`

## 4) Errores
- Patrón:
  - Título: `No se pudo completar la acción`
  - Mensaje: causa breve y accionable
  - CTA: `Reintentar`
- Evitar mensajes técnicos en UI final (logs internos se quedan en consola/backend).

## 5) Convenciones de tono
- Español neutro, directo, sin jerga interna.
- Frases de 4-10 palabras para CTAs.
- Consistencia terminológica:
  - `Panel` (no `Dashboard`)
  - `Seguimiento` (no `Watchlist`)
  - `Búsqueda rápida` (no `Quick search`)

## 6) Navegación privada (final ciclo 1)
- Panel
- Seguimiento
- Búsqueda rápida
- Alertas
- Recomendaciones
- Preferencias
- Ayuda
