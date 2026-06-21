**Estado:** vivo  
**Ultima revision:** 2026-06-16  
**Fuente de verdad:** si  
**Area:** reference

# Guia de lenguaje visible humanizado

## Objetivo

Convertir lenguaje tecnico, interno o mixto en copy visible claro, cercano y accionable para personas no tecnicas, sin tocar contratos, rutas, APIs, enums ni nombres internos.

## Reglas operativas

- Lo tecnico puede vivir en backend, logs, codigo y nombres internos; no en la UI visible.
- Cada texto visible debe responder al menos a una de estas preguntas: que pasa, me afecta, que hago ahora.
- Evitar mezcla ES/EN en texto visible, salvo labels de producto ya consolidados.
- `Watchlist` se conserva como nombre visible de producto.
- `Quick Search` se conserva como nombre visible de producto hasta nueva decision explicita.
- En estados, filtros, banners y ayudas manda la comprension por delante de la terminologia interna.
- La personalidad de Viru vive en el tono y en los nombres de producto, no en obligar a descifrar jerga tecnica.

## Terminos permitidos y evitar

| Evitar en UI visible | Usar en su lugar | Nota |
|---|---|---|
| modo degradado | resultados parciales / ultimo dato confirmado | Reservar `degraded` para backend y observabilidad |
| frescura | ultima comprobacion / comprobado hace | Hablar de tiempo real comprensible |
| score | valoracion Viru / mejor opcion / por que aparece arriba | Explicar el significado |
| heuristico | orden inteligente / criterio automatico | Evitar jerga tecnica |
| strict | modo estricto | Sin mezcla ES/EN |
| apertura | cobertura | Mejor describe el alcance |
| soporte parcial | datos parciales permitidos | Evita tono de atencion al cliente |
| revalidar | actualizar / comprobar de nuevo | Mas accionable |
| visto hace | comprobado hace | `visto` parece accion humana |
| workspace | panel / espacio de busqueda / espacio privado | Segun contexto |
| ranking | orden recomendado / como ordenamos | Hablar del beneficio |
| feedback de producto | enviar opinion | Mas natural |

## Labels de producto congelados

- `Watchlist` se mantiene como label visible de producto.
- `Quick Search` se mantiene como label visible de producto.
- `Oportunidades`, `Alertas`, `Preferencias` y `Ayuda` se mantienen como labels visibles canonicos.

## Aplicacion minima obligatoria

- Banners, notices y mensajes de disponibilidad parcial.
- Labels de antiguedad del dato.
- Filtros activos, tooltips y ayudas contextuales.
- Empty states, errores y llamadas a la accion.
- Documentacion publica que explica estados operativos al usuario.
