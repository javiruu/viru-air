# Fiabilidad y eficiencia del calendario de precios

**Estado:** aprobado
**Fecha:** 2026-08-21
**Área:** Quick Search

## Decisión

Mantener el contrato de `calendar-hints` y reforzar su ejecución con dos reglas:

1. Una instalación que añade las preferencias de búsqueda mediante compatibilidad de esquema debe adoptar el modo contextual, igual que la migración principal.
2. Cuando ya hay observaciones frescas para parte del mes, la planificación de rutas amplias solo puede usar como anclas los días que aún requieren proveedor.

## Invariantes

- Los datos frescos se reutilizan antes de solicitar al proveedor.
- La referencia contextual no mezcla monedas, tramos ni cobertura parcial.
- Los campos diarios continúan expresando precio, calidad y causa de forma independiente.
- La optimización no cambia la tarifa ni el color de los días cubiertos.

## Verificación

- Regresión de esquema legado que inserta una preferencia después de la actualización compatible.
- Regresión de scope amplio parcialmente reutilizado que comprueba que el proveedor solo recibe el día pendiente.
- Pruebas de calendario, preferencias, lint, migración y petición HTTP real.
