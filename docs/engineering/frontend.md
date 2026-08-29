# Frontend

**Estado:** vivo  
**Última revisión:** 2026-08-29
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
