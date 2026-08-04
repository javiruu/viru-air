# Centro de notificaciones persistente

**Estado:** vivo
**Ultima revision:** 2026-08-04
**Fuente de verdad:** si
**Area:** producto

## Proposito

`/notifications` es el centro privado de Señales de Viru. Reune la bandeja persistente y la configuracion de reglas en una sola superficie con dos vistas: `Bandeja` y `Reglas`.

La ruta historica `/alerts` se conserva como alias compatible y redirige a `/notifications?view=rules`, preservando los parametros de consulta. Las APIs `/api/v1/alerts/*` no cambian.

La bandeja complementa los toast in-app: los toast avisan en el momento, pero esta pantalla conserva el rastro consultable para decisiones posteriores.

La bandeja existe para senales que no deben perderse:

- cambios de precio de alertas;
- tendencias comunitarias de rutas vigiladas;
- senales hoteleras del radar de hoteles;
- actividad de seguridad;
- digest de alertas agrupadas;
- incidencias de workers o entregas fallidas.

## Experiencia actual

La vista `Bandeja` de `/notifications` muestra:

- un checklist de cabina que prioriza senales sin leer con una accion concreta;
- resumen reciente por total, precio, seguridad, digest, worker y comunidad, sin mezclar esas cifras globales con las de una ruta;
- filtros por categoria, estado sin leer y `Para actuar` (tambien enlazable con `?filter=actionable`);
- cronologia visual por hoy, ultimos siete dias y anteriores, sin colapsar ni alterar los eventos fuente;
- acciones para marcar una senal como leida o marcar toda la bandeja como leida;
- contador de senales sin leer en la navegacion privada;
- acceso interno a `Reglas` para decidir que debe vigilar Viru.

La vista `Reglas` mantiene la configuracion existente de alertas de precio, horas tranquilas, simulacion, entregas e historial. Suma una lectura conectada de la ruta seleccionada: reglas activas/pausadas, cooldown minimo y ultima evaluacion, con acceso directo a las senales pendientes. Esta lectura reutiliza el estado ya cargado y no anade endpoints ni polling. Cuando el alias legado incluye `watch_id`, la vista selecciona ese seguimiento si sigue disponible para el usuario.

La respuesta de Bandeja se normaliza en la frontera HTTP para tolerar colecciones o campos opcionales ausentes y el envelope legado en forma de array. Las filas sin identidad fuente segura se descartan, porque el estado de lectura debe conservar exactamente `source_type` y `source_id`.

La identidad visual sigue el contrato dual-theme de Viru: clara y oscura con el mismo tono calido/aeronautico, sin convertir la bandeja en un panel SaaS generico.

## Estados

- Una senal es `Sin leer` cuando no existe registro de lectura para el usuario y la fuente.
- Una senal es `Leida` cuando `user_notification_state.read_at` existe.
- El estado de lectura es privado por usuario y no modifica el evento original.

## Fuentes

La bandeja no introduce un pipeline paralelo. Agrega fuentes existentes y les suma estado de lectura:

- `notification_event`: eventos emitidos por alertas, digests y workers.
- `hotel_alert_event`: eventos emitidos por reglas hoteleras o hoteles trackeados por el usuario.
- `security_activity`: actividad sensible de cuenta.
- `community_trending`: snapshot persistente de rutas en tendencia, visible solo cuando el usuario tiene una Watch activa para esa dirección.

Las señales comunitarias no son alertas personalizadas de precio ni identifican a otros viajeros. Desaparecen cuando el snapshot deja de estar publicado o caduca.

El contrato tecnico de endpoints, tipos y persistencia esta en `docs/reference/backend/notifications-contract.md`.
