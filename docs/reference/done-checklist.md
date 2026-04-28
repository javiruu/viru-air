# Done Checklist (Viru Tracker)

Usa esta lista para cerrar cualquier tarea de codigo en `viru-tracker`.

## 1) Analisis y alcance

- [ ] Se declaran supuestos clave (o se aclaran dudas bloqueantes).
- [ ] Se define plan corto para tareas no triviales.
- [ ] El cambio es quirurgico (sin refactors no pedidos).

## 2) Verificacion tecnica

- [ ] Se reprodujo el problema o caso objetivo antes del parche (cuando aplica).
- [ ] Se valido con checks relevantes (tests/build/lint segun impacto).
- [ ] Si el cambio es visible en navegador, hay evidencia real:
  - [ ] TestSprite, o
  - [ ] Capturas del flujo real en navegador.

## 3) Evidencia obligatoria para UI/browser

- [ ] Ruta exacta verificada.
- [ ] Interaccion exacta ejecutada.
- [ ] Resultado visible observado.
- [ ] Limitaciones o incertidumbres (si existen).

## 4) Publicacion obligatoria

- [ ] Cambios hechos en checkout canonico: `_publish_repo`.
- [ ] Diff revisado y acotado al pedido.
- [ ] Commit Conventional Commit en `main`.
- [ ] Push confirmado a `origin/main`.
- [ ] Hash final reportado al usuario.

## 5) Formato de cierre

- [ ] Root cause
- [ ] Files changed
- [ ] Verification
- [ ] Publish status (commit + push)

