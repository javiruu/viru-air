# Done Checklist (Viru Tracker)

Usa esta lista para cerrar cualquier tarea en `viru-tracker`, especialmente cuando
la sesion mezcla investigacion, parche, validacion y publicacion.

## 1) Investigado

- [ ] Se declaran supuestos clave (o se aclaran dudas bloqueantes).
- [ ] Se define plan corto para tareas no triviales.
- [ ] Se identifican alcance real, riesgo y fuente de verdad aplicable.

## 2) Parchado

- [ ] El cambio es quirurgico (sin refactors no pedidos).
- [ ] Solo se tocan archivos trazables al pedido.
- [ ] Si la tarea era solo auditoria o documentacion, queda explicito que no hubo parche de logica.

## 3) Verificado

- [ ] Se reprodujo el problema o caso objetivo antes del parche (cuando aplica).
- [ ] Se valido con checks relevantes (tests/build/lint segun impacto).
- [ ] Si el cambio es visible en navegador, se deja claro si la validacion manual humana ya ocurrio o sigue pendiente.

## 4) Evidencia obligatoria para UI/browser

- [ ] Ruta exacta verificada.
- [ ] Interaccion exacta ejecutada.
- [ ] Resultado visible observado.
- [ ] Limitaciones o incertidumbres (si existen).

Nota: para cambios UI visibles, la revision manual del usuario en navegador real
sigue siendo obligatoria. Para tareas documentales o procesales como las Fases 1-5
del roadmap, no aplica como gate de cierre si no hubo cambio visible.

## 5) Publicado

- [ ] Cambios hechos en checkout canonico: raiz del repo (`viru-tracker`).
- [ ] Diff revisado y acotado al pedido.
- [ ] Commit Conventional Commit en `main`.
- [ ] Push confirmado a `origin/main`.
- [ ] Hash final reportado al usuario.

## 6) Formato de cierre

- [ ] Root cause
- [ ] Files changed
- [ ] Verification
- [ ] Publish status (commit + push)
