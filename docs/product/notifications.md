# Centro de notificaciones persistente

**Estado:** vivo
**Ultima revision:** 2026-07-03
**Fuente de verdad:** si
**Area:** producto

## Proposito

`/notifications` es la bandeja persistente de señales privadas de Viru. Complementa los toast in-app: los toast avisan en el momento, pero esta pantalla conserva el rastro consultable para decisiones posteriores.

La bandeja existe para senales que no deben perderse:

- cambios de precio de alertas;
- actividad de seguridad;
- digest de alertas agrupadas;
- incidencias de workers o entregas fallidas.

## Experiencia actual

La pantalla privada `/notifications` muestra:

- resumen por total, sin leer, precio, seguridad, digest y workers;
- filtros por categoria y estado sin leer;
- lista cronologica de senales con titulo, descripcion, hora relativa, ruta cuando aplica y accion de apertura;
- acciones para marcar una senal como leida o marcar toda la bandeja como leida;
- enlace directo a `/alerts` para ajustar alertas de precio.

La identidad visual sigue el contrato dual-theme de Viru: clara y oscura con el mismo tono calido/aeronautico, sin convertir la bandeja en un panel SaaS generico.

## Estados

- Una senal es `Sin leer` cuando no existe registro de lectura para el usuario y la fuente.
- Una senal es `Leida` cuando `user_notification_state.read_at` existe.
- El estado de lectura es privado por usuario y no modifica el evento original.

## Fuentes

La bandeja no introduce un pipeline paralelo. Agrega fuentes existentes y les suma estado de lectura:

- `notification_event`: eventos emitidos por alertas, digests y workers.
- `security_activity`: actividad sensible de cuenta.

El contrato tecnico de endpoints, tipos y persistencia esta en `docs/reference/backend/notifications-contract.md`.
