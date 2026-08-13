# Hotels Product Direction

**Estado:** vivo  
**Última revisión:** 2026-06-04 (cierre Fase 10)  
**Fuente de verdad:** sí  
**Área:** producto / hotels

> 🟢 **Plan completado.** Las 10 fases definidas en este documento están implementadas, testeadas y verificadas. Ver sección 13 (Estado de implementación) para el detalle por fase.

## 1. Qué será /hoteles

/hoteles será un **comparador y tracker diario de precios hoteleros** tipo Trivago, integrado en Viru Air.

El usuario podrá:

- Buscar hoteles cerca de un área específica (ciudad, zona, coordenadas).
- Filtrar por fechas de check-in/check-out, huéspedes, estrellas mínimas y precio máximo.
- Ver resultados comparables por precio, proveedor, distancia y estrellas.
- Guardar una oferta concreta (hotel + fechas + huéspedes + proveedor + precio inicial) para que Viru **trackee ese precio cada día**, igual que /watchlist hace con vuelos.
- Ver el histórico de precios de cada oferta trackeada.
- Configurar alertas humanas de precio (bajada, subida, cambio de proveedor, disponibilidad).
- Consultar diferencias entre proveedores y hoteles cercanos como **extras secundarios**, no como protagonistas.

## 2. Qué NO será

/hoteles **NO** será:

- Una plataforma de "inteligencia hotelera B2B".
- Un panel técnico de análisis de comp sets y paridad como fin en sí mismo.
- Un gestor de sets competitivos profesionales.
- Un dashboard de revenue management.
- Un producto exclusivo para hoteleros o analistas de pricing.

El lenguaje, la jerarquía visual y el flujo principal deben hablar a un **usuario final que quiere encontrar y seguir el precio de un hotel**, no a un analista de mercado.

## 3. Qué piezas actuales se conservan

Todas las piezas existentes se **conservan**. Ninguna se borra.

| Pieza | Se conserva | Rol futuro |
|---|---|---|
| `HotelProperty` | Sí | Catálogo de hoteles |
| `HotelRateSnapshot` | Sí | Snapshots de precio (se amplían en Fase 3) |
| `HotelWatchlistItem` | Sí | Se mantiene, pero **no es el tracking final** |
| `HotelCompSet` / `HotelCompSetMember` | Sí | Se relega a extra "Hoteles cercanos" |
| `HotelAlertRule` / `HotelAlertEvent` | Sí | Se reorientan a tracked offers (Fase 9) |
| `HotelProviderRun` | Sí | Se mantiene para trazabilidad de sweeps |
| `HotelProviderAlias` | Sí | Mapeo de proveedores |
| Paridad (`HotelParityService`) | Sí | Se relega a extra "Diferencia entre proveedores" |
| Makcorps provider | Sí | Se conserva como provider opcional |
| Mock provider | Sí | Se mantiene para desarrollo y tests |
| `run_hotel_sweep` | Sí | Se reorienta a revisar tracked offers (Fase 8) |

## 4. Qué piezas se renombran o relegan

### Renombres de cara al usuario (Fase 6)

| Nombre actual | Nuevo nombre |
|---|---|
| Radar hotelero | Hoteles / Rastreador hotelero |
| Comp set | Hoteles cercanos / Comparativa de zona |
| Paridad | Diferencia entre proveedores |
| Alert rules | Alertas de precio |
| Alert events | Cambios detectados |
| Sweep | Revisión diaria |

### Relegación de funcionalidad

- **Comp sets**: pasan de ser el centro a ser un extra plegable. Se mantiene la API y los datos, pero la UI los relega a segundo plano.
- **Paridad**: se mantiene el cálculo, pero se presenta como "Diferencia entre proveedores", una información complementaria, no el foco.
- **Alertas técnicas** (`parity_break`): se mantienen como alerta avanzada, no como opción principal. Las alertas visibles para el usuario son humanas (Fase 9).

## 5. Flujo UX principal

```
1. Usuario llega a /hoteles
2. Ve un buscador con:
   - Zona/área (texto → coordenadas)
   - Fechas (check-in / check-out)
   - Huéspedes
   - Filtros opcionales (estrellas, precio máx)
3. Pulsa "Buscar"
4. Ve lista de resultados con:
   - Nombre del hotel
   - Ciudad
   - Estrellas
   - Distancia desde el centro del área
   - Precio más bajo encontrado
   - Proveedor
   - Botón "Trackear precio"
5. Puede pulsar "Trackear precio" en una oferta
6. La oferta se guarda como HotelTrackedOffer
7. Aparece en "Seguimientos activos"
8. Cada día, el sweep revisa los tracked offers activos
9. El usuario puede ver el histórico de precios
10. Puede configurar alertas: "Avísame si baja de X €"
```

## 6. Modelo de datos objetivo

### Entidades principales

```
HotelProperty (existente)
  → catálogo de hoteles

HotelRateSnapshot (existente, ampliado en Fase 3)
  → snapshot de precio en un momento dado
  → se vincula opcionalmente a HotelTrackedOffer

HotelTrackedOffer (nuevo — Fase 2)
  → una oferta concreta que el usuario quiere trackear
  → guarda hotel_id, fechas, huéspedes, proveedor, precios, zona

HotelProviderRun (existente)
  → trazabilidad de cada ejecución de sweep

HotelAlertRule / HotelAlertEvent (existente, reorientados en Fase 9)
  → reglas de alerta y eventos disparados

HotelCompSet / HotelCompSetMember (existente, relegado)
  → sets competitivos (extra secundario)

HotelWatchlistItem (existente, mantenido)
  → watchlist simple (no es el tracking final)
```

### Relaciones clave

```
User 1→N HotelTrackedOffer
HotelProperty 1→N HotelTrackedOffer
HotelTrackedOffer 1→N HotelRateSnapshot
HotelTrackedOffer 1→N HotelAlertRule
```

## 7. Qué pasa con comp sets

- **Se conservan** en backend: modelos, API y datos no se tocan.
- **Se relegan en UI**: pasan de ser el centro a ser un panel plegable llamado "Hoteles cercanos" o "Comparativa de zona".
- **No se usan** para el flujo principal de búsqueda por área (Fase 4).
- Pueden servir como fuente de sugerencias de hoteles cercanos para enriquecer resultados.

## 8. Qué pasa con paridad

- **Se conserva** el cálculo de paridad (`HotelParityService`).
- **Se renombra** en UI a "Diferencia entre proveedores".
- **Se relega** a un extra secundario, accesible desde el detalle de un hotel o una oferta trackeada.
- **No es el foco** de la pantalla principal.

## 9. Qué pasa con Makcorps

- **Se conserva** como provider opcional.
- Se mantiene el adapter `MakcorpsProvider`.
- Se usa si está disponible, pero **no es requisito** para el funcionamiento del comparador/tracker.
- El mock provider sigue siendo el proveedor por defecto para desarrollo.
- El sweep con Makcorps se reorienta a revisar tracked offers (Fase 8).

## 10. Plan de migración en 10 fases

| Fase | Descripción | Tipo |
|---|---|---|
| 1 | Redefinir producto y congelar dirección (este documento) | Docs | ✅ |
| 2 | Crear modelo HotelTrackedOffer + CRUD + endpoints | Backend | ✅ |
| 3 | Separar "oferta actual" de "snapshot histórico" (ampliar HotelRateSnapshot) | Backend | ✅ |
| 4 | Búsqueda por área real (lat/lng/radius) | Backend | ✅ |
| 5 | Resolver destino/zona desde texto | Backend | ✅ |
| 6 | Reordenar UI como comparador tipo Trivago | Frontend | ✅ |
| 7 | Guardar una oferta desde resultados | Full-stack | ✅ |
| 8 | Revisión diaria real de tracked offers | Backend | ✅ |
| 9 | Alertas humanas de precio | Full-stack | ✅ |
| 10 | QA final, limpieza conceptual y documentación | QA/Docs | ✅ |

## 11. Riesgos

- **Makcorps no acepta zona/fechas/huéspedes como Trivago real**: no prometerlo como tal. El mock provider cubre el MVP.
- **HotelWatchlistItem no es tracking final**: no confundirlo con HotelTrackedOffer. Se mantienen ambos; el nuevo es el que trackea de verdad.
- **No borrar comp sets ni paridad**: el plan es relegar, no eliminar. Si se borran, se pierde funcionalidad que puede ser útil como extra.
- **No mezclar backend + rediseño visual + provider real en una sola fase**: cada fase tiene un alcance acotado.

## 12. Criterios de aceptación (visión global)

Al finalizar las 10 fases:

1. /hoteles busca por zona, fechas y huéspedes.
2. Devuelve resultados tipo comparador con precio, proveedor, distancia y estrellas.
3. Se puede trackear una oferta concreta (hotel + fechas + huéspedes + proveedor).
4. Se guarda snapshot inicial al crear el tracking.
5. El sweep diario genera snapshots para tracked offers activos.
6. Se ve el histórico de precios de cada oferta trackeada.
7. Se ven cambios de precio detectados.
8. Las alertas son humanas ("Avísame si baja de X €").
9. Comp sets y paridad quedan como extras secundarios.
10. Dark/light/responsive correcto.
11. La documentación está actualizada.

## 13. Estado de implementación (cierre Fase 10 — 2026-06-04)

Todas las fases del plan están completadas:

| Fase | Descripción | Evidencia |
|---|---|---|
| 1 | Spec producto | `docs/specs/hotels-product-direction.md` |
| 2 | `HotelTrackedOffer` + CRUD | Modelo, migración 0020, 5 endpoints, tests |
| 3 | Snapshots asociados | `HotelRateSnapshot` ampliado, endpoint `/tracked-offers/{id}/snapshots`, migración 0021 |
| 4 | Búsqueda por área | `GET /area-search` con 10 params, Haversine, ordenación |
| 5 | Resolver zona desde texto | `GET /area-resolve?q=`, centroide desde datos internos |
| 6 | UI comparador | Layout reorganizado, paneles colapsables, copy humano |
| 7 | Trackear precio desde resultados | Botón "Trackear precio", snapshot inicial, prevención de duplicados |
| 8 | Sweep diario de tracked offers | `sweep_tracked_offers` integrado en `run_hotel_sweep`, actualización de `current_price`, eventos de cambio |
| 9 | Alertas humanas | 6 tipos de alerta (baja/subida por €/%, proveedor, disponibilidad), UI con lenguaje humano |
| 10 | QA final y documentación | 5 docs actualizados, 132 tests, build frontend OK |

### Deudas futuras

1. **Provider real dinámico**: Makcorps y futuros providers deben aceptar zona/fechas/huéspedes para que el sweep produzca snapshots nuevos en cada ejecución.
2. **Scheduler automático**: Los sweeps se ejecutan manualmente o vía worker opcional. No hay scheduler integrado en el startup del API.
3. **Verificación visual manual**: La QA visual en navegador real (dark/light/responsive) queda pendiente.
4. **`DELETE /comp-sets/{id}`**: Cerrado en la implementación V1 y cubierto por tests de ownership; mantener QA visual del control.
5. **Geocoder externo**: La resolución externa está habilitada detrás de `HOTEL_GEOCODER_ENABLED`; siguen pendientes la calibración de cobertura, coste, cache y límites para producción.
6. **Alertas sobre `initial_price`**: Cerrado en H26/HISTORY. `compare_against="initial_price"` ya permite que las reglas porcentuales comparen contra el baseline original; se conserva como opción explícita frente a `snapshot_previous`.
