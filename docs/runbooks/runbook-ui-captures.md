# Runbook UI Captures (Reusable)

## Objetivo

Definir un flujo reutilizable para obtener evidencia visual de cambios UI (capturas) en `viru-tracker`, sin depender de memoria de conversacion.

## Reglas base

- Guarda evidencia en `docs/qa/`.
- Usa nombres explicitos por feature + viewport + tipo:
  - `docs/qa/<feature>-<viewport>-full.png`
  - `docs/qa/<feature>-<viewport>-section.png`
  - `docs/qa/<feature>-<viewport>-component.png`
- No publiques scripts temporales `_tmp_*`.
- Si creas un flujo reutilizable, conviertelo en script estable en `frontend/scripts/` con prefijo `qa_`.
- Nunca incluir secretos/tokens en capturas, logs o markdown.

## Flujo estandar de capturas

1. Levantar servicios necesarios (frontend y backend si la pantalla depende de API/autenticacion).
2. Abrir la ruta real en navegador (Playwright o TestSprite).
3. Reproducir la interaccion exacta del caso.
4. Capturar como minimo:
   - una captura full page
   - una captura de la seccion cambiada
   - una captura del componente cambiado
5. Repetir al menos en:
   - desktop (ej. `1440x900`)
   - mobile (ej. `390x844` o `375x812`)
6. Guardar en `docs/qa/` y reportar rutas absolutas en el resumen final.

## Autenticacion reutilizable (cuando aplica)

- Si la ruta es privada, autentica en la UI y verifica que existe token local:
  - clave esperada: `viru_token` (localStorage).
- Credenciales semilla de desarrollo (si backend arranca con seed):
  - `user@viru.local` / `ViruUser123`
- Si el login no redirige automaticamente, volver a cargar la ruta objetivo tras guardar token.

## Dependencias externas no fiables (clima, providers, etc.)

Cuando el estado visual depende de un proveedor externo inestable:

- Primero intentar flujo real.
- Si bloquea la verificacion visual, mockear solo el endpoint externo en Playwright (`page.route`) para forzar el estado UI.
- Documentar en el reporte final que se uso mock visual y que la logica funcional no se modifico por ese mock.

## Estructura recomendada para scripts

- Ubicacion: `frontend/scripts/qa_capture_<feature>.mjs`
- Responsabilidades:
  - abrir ruta
  - autenticar si aplica
  - ejecutar interaccion concreta
  - generar capturas desktop/mobile
  - escribir archivos en `docs/qa/`

Comando recomendado:

```powershell
node frontend/scripts/qa_capture_<feature>.mjs
```

## Mantenimiento para futuras conversaciones

Si en otra conversacion hace falta una captura con flujo nuevo:

1. Reutilizar un script existente `qa_capture_*` si cubre el caso.
2. Si no cubre, crear o ampliar un script estable (no `_tmp`).
3. Actualizar este runbook en una seccion nueva de "Recetas" con:
   - objetivo del flujo
   - comando
   - archivos de salida esperados
   - limitaciones conocidas

## Recetas

### Receta: Quick Search Weather Card

- Objetivo: capturar evidencia visual de `/quick-search` en ruta privada con sesion autenticada.
- Comando canonico:

```powershell
npm.cmd run qa:visual:quick-search
```

- Credenciales QA por defecto (seed local): `user@viru.local` / `ViruUser123`.
- Override por entorno (si no usas seed):
  - `QA_LOGIN_EMAIL`
  - `QA_LOGIN_PASSWORD`
- El script ahora:
  1. intenta abrir `/quick-search`;
  2. si detecta redireccion a `/login`, completa login automaticamente;
  3. vuelve a `/quick-search` y captura evidencias;
  4. expande el primer detalle cuando existe y reporta si detecta `.qs-result-weather`.
- Salidas esperadas:
  - `docs/qa/quick-search-visual-report.json`
  - `docs/qa/snapshots_quick-search-desktop.png`
  - `docs/qa/snapshots_quick-search-tablet768.png`
  - `docs/qa/snapshots_quick-search-mobile375.png`
  - `docs/qa/snapshots_quick-search-mobile320.png`
- Nota: si el proveedor meteo no responde, usar mock de `https://api.open-meteo.com/v1/forecast` solo para materializar el estado visual.
