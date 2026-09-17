# Viru API Layer

Este módulo centraliza la interacción tipada con el backend de Viru Tracker.

- `src/api/generated/`: Código TypeScript y modelos generados automáticamente mediante **Orval v8**. No editar manualmente.
- `src/api/mutator/`: Adaptadores de transporte y mutators (`custom-client.ts`) que inyectan autenticación JWT, correlation IDs y resolución de URL base.

### Comandos
- Regenerar cliente: `npm run api:generate`
- Verificar sincronización en CI: `npm run api:check`

