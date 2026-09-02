# Frontend

**Estado:** vivo  
**Última revisión:** 2026-09-02
**Fuente de verdad:** sí  
**Área:** engineering

## Resumen

El frontend de Viru Air está construido con Next.js, React y TypeScript, y usa un contrato visual documentado para evitar deriva de UI.

## Contenido principal

- Stack visible: Next.js 15, React 19, TypeScript.
- La guía viva del sistema visual está en [DESIGN.md](../../DESIGN.md).
- La skill `/.codex/skills/viru-air-ui/SKILL.md` obliga a leerla antes del trabajo UI.
- Las specs UI activas están en:
  - [Specs activas](../specs/README.md)

## Arquitectura de estilos de pantalla

- `frontend/src/styles/screens.css` es el punto de entrada estable y contiene únicamente imports ordenados.
- Las reglas viven en `frontend/src/styles/screens/`, separadas por dominio (`quick-search`, `watchlist`, `door-to-door`, `hotels`, `private`, `public`, `shared` y `foundation`).
- El orden del manifiesto es parte del contrato: algunos módulos finales refinan reglas anteriores. No reordenar imports para agruparlos visualmente sin comprobar la cascada renderizada.
- Una regla exclusiva permanece en su dominio. Sólo los patrones realmente usados por varias pantallas pasan a `shared`, `components.css` o `tokens.css`.
- Antes de cerrar cambios en este árbol, ejecutar desde `frontend`:

  ```bash
  npm run styles:verify
  ```

  La comprobación rechaza imports duplicados, módulos ausentes o huérfanos, CSS inválido y archivos que vuelvan a superar 3.000 líneas.

## Estados de carga Boneyard

- Los estados de carga del frontend se generan con `boneyard-js`; no se mantiene un primitivo local paralelo.
- Las definiciones generadas viven en `frontend/src/bones/` y se registran desde `frontend/src/modules/shared/BoneyardLoad.tsx`.
- Tras cambiar la estructura de una referencia de carga, iniciar el frontend y ejecutar desde `frontend`:

  ```bash
  npm run bones:build -- http://localhost:3000/boneyard-capture --force
  ```

- `/boneyard-capture` existe solo en desarrollo y reúne todos los estados nombrados para regenerarlos. Añadir `?review=1` oculta el overlay de navegación para revisar visualmente la galería; `?review=1&theme=dark` permite comprobar sus colores oscuros. La configuración conserva los colores cálidos de ambos temas en `frontend/boneyard.config.json`.

## Relacionado

- [Product dashboard](../product/dashboard.md)
- [Product quick search](../product/quick-search.md)
- [QA frontend](../qa/README.md)
