Status: reference
Scope: reusable QA reference or checklist
Last reviewed: 2026-04-15
Canonical source: docs/qa/frontend-pr-checklist.md
Related: docs/qa/README.md, docs/archive/qa/README.md

---
# H3. Modales accesibles y consistentes
- [x] Todos los modales usan `role="dialog"` y `aria-modal="true"`.
- [x] Botones de cierre icon-only tienen `aria-label`.
- [x] `Escape` y click fuera cierran modal de forma consistente.

Aceptacion:
- Coherencia entre watchlist y quick-search.

Verificacion:
```powershell
rg -n "role=\"dialog\"|aria-modal|modal-close|>x<|>X<" frontend/src
```

---

### H4. Copy e idioma consistentes
- [x] Sin mezcla ES/EN dentro del mismo bloque funcional (ej. alerts).
- [x] Uso consistente de acentos y microcopy (ej. `Atras` vs `Atras/Atrás` definido por criterio de producto).
- [ ] Textos de estado y errores siguen misma convencion.

Aceptacion:
- Alerts 100% coherente con idioma activo.

Verificacion:
```powershell
rg -n "Category|No results|Atras|Atrás|Historico|Histórico" frontend/src/app
```

---

### H5. Fechas y horas localizadas de forma uniforme
- [x] Todas las fechas visibles de UI usan locale explicito o helper central.
- [x] Se evita `toLocaleString()` sin locale en componentes de usuario.

Aceptacion:
- Formato consistente en history/alerts/admin/dashboard.

Verificacion:
```powershell
rg -n "toLocaleString\(" frontend/src/app
```

---

### H6. API client robusto para metodos GET/JSON
- [x] No se fuerza `Content-Type: application/json` cuando no hay body.
- [x] Se mantiene `x-correlation-id`.
- [x] No hay regresion en auth headers.

Aceptacion:
- Requests GET limpias y comportamiento auth igual que antes.

Verificacion:
```powershell
Get-Content -Raw frontend/src/modules/shared/api.ts
```

---

### H7. Warning CSS de autoprefixer resuelto
- [x] Reemplazar valores `start` por valor compatible cuando corresponda (`flex-start`).
- [ ] `frontend_next_dev.err.log` no muestra warning repetido por esa regla.

Aceptacion:
- Sin warning de `autoprefixer: start value has mixed support`.

Verificacion:
```powershell
rg -n "align-content:\s*start|align-items:\s*start" frontend/src/styles/globals.css
rg -n "autoprefixer: start value has mixed support" logs/frontend_next_dev.err.log
```

---

### H8. Reduccion de complejidad (quick-search/watchlist)
- [x] Definir y ejecutar plan de extraccion por componentes/hooks.
- [ ] `quick-search/page.tsx` y `watchlist/page.tsx` bajan complejidad ciclomatica y lineas.
- [ ] Cobertura minima para helpers extraidos.

Aceptacion:
- Modulos grandes divididos por responsabilidades (formulario, resultados, modales, hooks de datos).

Verificacion:
```powershell
(Get-Content frontend/src/app/(private)/quick-search/page.tsx).Length
(Get-Content frontend/src/app/(private)/watchlist/page.tsx).Length
```

## 3) Evidencia obligatoria en PR
- [ ] Capturas antes/despues de cada modulo tocado.
- [x] Resultado de `npm run test`.
- [x] Resultado de `npm run lint`.
- [x] Lista de hallazgos cerrados (`H1...H8`) con referencia de archivo.
- [ ] Riesgos residuales y plan de seguimiento (si aplica).

## 4) Checklist de cierre
- [ ] UX mas simple para usuario final (menos duplicidad, menos ruido).
- [x] A11y mejorada (modal, cierres, foco, labels).
- [x] Coherencia de lenguaje y formatos.
- [ ] Menor deuda tecnica en modulos criticos.
- [ ] PR lista para review funcional + QA visual.





