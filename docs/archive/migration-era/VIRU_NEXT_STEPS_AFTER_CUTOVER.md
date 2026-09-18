# VIRU — NEXT STEPS AFTER CUTOVER & HARDENING

> **Propósito:** este documento reemplaza los planes anteriores como guía de **qué hacer a continuación**.
> No es otro programa de modernización masiva.
> El objetivo ahora es **cerrar lo que todavía está en shadow / local-only**, consolidar el estado seguro ya conseguido y volver cuanto antes al desarrollo normal de producto.

---

## 0. CONTEXTO QUE DEBE ACEPTARSE COMO BASE

El repositorio ha pasado por:

1. modernización de frontend/backend;
2. eliminación de Docker y contenedores;
3. migración del ownership de esquema hacia `supabase/migrations`;
4. eliminación del fallback SQLite del runtime principal;
5. retirada de Alembic del runtime/dependencies;
6. adopción inicial de Supabase Auth;
7. generación OpenAPI + Orval;
8. introducción de TanStack Query, Zod, shadcn/ui, PostHog y OpenTelemetry;
9. formateo global Biome;
10. hardening de seguridad posterior mediante code review adversarial.

El último hardening corrigió hallazgos críticos reales:

- bypass JWT con secreto vacío;
- auto-provisionamiento inseguro a partir de claims;
- elevación a admin desde claims;
- mocks silenciosos de Supabase en producción;
- auditoría de IP/UA falsa;
- limpieza incompleta de tokens legacy;
- falsos positivos E2E de autenticación;
- inconsistencias de tests tras el cutover.

El último estado local conocido terminó con:

- backend completo verde;
- frontend unit/integration verde;
- E2E Playwright verde;
- TypeScript verde;
- ESLint verde;
- Biome sin errores bloqueantes;
- OpenAPI/Orval sin drift;
- build de producción verde;
- `npm audit` sin vulnerabilidades reportadas;
- review de seguridad pasando de **Request Changes** a **Approved**.

**IMPORTANTE:** no asumir que porque lo anterior está verde todo el cutover está terminado en producción.
Todavía hay trabajo de **validación remota, adopción real y publicación**.

---

# REGLAS GLOBALES

## Regla 1 — No introducir tecnologías nuevas

NO añadir:

- otro ORM;
- otro cliente HTTP;
- otra librería de auth;
- otro sistema de migraciones;
- Redis/Valkey salvo necesidad medible futura;
- Typesense;
- Trigger.dev;
- Temporal;
- Docker;
- Kubernetes adicional;
- abstracciones nuevas "por limpieza".

Primero terminar de aprovechar lo que ya existe.

## Regla 2 — Docker sigue prohibido

El proyecto debe funcionar sin:

- `Dockerfile`;
- `docker-compose*`;
- `docker build`;
- `docker run`;
- `supabase start`;
- `supabase db reset` local si requiere Docker;
- CI dependiente de Docker;
- documentación que obligue a Docker.

Supabase se valida mediante proyectos remotos de DEV/STAGING aislados.

## Regla 3 — Truth before change

Antes de cada fase:

1. medir estado real;
2. guardar contadores;
3. ejecutar tests baseline;
4. hacer cambios;
5. volver a medir;
6. comparar;
7. no declarar DONE sin evidencia.

Nunca confiar en un JSON/proof viejo si contradice el código.

## Regla 4 — No volver a hacer mega-refactors

El gran cutover ya ocurrió.

Desde ahora:

- cambios pequeños;
- un dominio cada vez;
- tests antes/después;
- commits fáciles de revertir;
- no mezclar formatter masivo con cambios funcionales.

## Regla 5 — Fail closed

Si falta una configuración crítica:

- DB;
- Supabase URL;
- publishable key;
- JWT verification config;
- backend secret requerido;
- proyecto STAGING;

la aplicación debe fallar claramente.

Nunca volver a:

```text
config ausente
    ↓
fallback silencioso
    ↓
"parece funcionar"
```

---


# GITHUB — REGLA OBLIGATORIA DE SINCRONIZACIÓN

A partir de este roadmap, GitHub debe mantenerse actualizado durante el trabajo.

No volver a acumular cientos de archivos modificados sin commit/push.

## Principio

Cada slice funcional terminado y verificado debe acabar en:

```text
change
  ↓
tests / gates
  ↓
git diff review
  ↓
commit
  ↓
push
  ↓
remote verified
```

Codex NO debe considerar una fase terminada si el cambio correspondiente sigue únicamente en el working tree, salvo que exista una razón explícita y documentada.

---

## Preflight Git obligatorio

Antes de empezar cualquier fase:

```bash
git status --short
git branch --show-current
git remote -v
git fetch --prune
git status -sb
```

Verificar:

- rama actual;
- remote correcto;
- si la rama local está ahead/behind;
- cambios locales existentes;
- archivos untracked;
- conflictos;
- commits remotos nuevos.

Si el remoto contiene cambios nuevos:

```text
NO hacer push a ciegas.
```

Primero integrar de forma segura.

Preferir:

```bash
git pull --rebase
```

solo cuando el working tree esté limpio o los cambios estén correctamente guardados/commiteados.

Nunca usar `git reset --hard` para resolver divergencias sin una razón explícita.

---

## Política de ramas

Si se está trabajando directamente sobre `main` y el repositorio lo permite:

- mantener commits pequeños y coherentes;
- ejecutar gates antes de push;
- nunca reescribir historial ya publicado.

Para cambios grandes o de riesgo:

```text
main
  ↓
feature/<scope>
  ↓
commits pequeños
  ↓
push
  ↓
review
  ↓
merge
```

Ejemplos:

```text
feature/supabase-remote-validation
feature/orval-watchlist-migration
fix/supabase-auth-hardening
chore/biome-format
```

No crear ramas innecesarias para cambios triviales.

---

## Política de commits

Cada commit debe representar una intención clara.

Formato recomendado:

```text
feat(scope): ...
fix(scope): ...
refactor(scope): ...
test(scope): ...
chore(scope): ...
docs(scope): ...
security(scope): ...
```

Ejemplos:

```text
security(auth): harden Supabase JWT verification
fix(auth): remove legacy token storage fallback
refactor(watchlist): migrate data access to Orval queries
test(rls): add remote cross-user isolation matrix
chore(frontend): apply canonical Biome formatting
docs(cutover): record staging verification results
```

Evitar:

```text
update
changes
final
fix stuff
codex changes
misc
```

---

## Qué debe ocurrir antes de cada commit

1. revisar:
   ```bash
   git diff
   git diff --check
   ```
2. comprobar que no hay secretos;
3. comprobar que no entra `.env`, DB local, dumps o claves;
4. ejecutar tests/gates proporcionales;
5. revisar archivos staged:
   ```bash
   git diff --cached --stat
   git diff --cached
   ```
6. commit.

Nunca usar:

```bash
git add .
```

a ciegas sobre un working tree grande.

Preferir staging deliberado:

```bash
git add <archivos concretos>
```

o:

```bash
git add -p
```

cuando convenga separar cambios.

---

## Push obligatorio por slice

Después de un commit validado:

```bash
git push
```

Si la rama todavía no existe remotamente:

```bash
git push -u origin <branch>
```

Después del push comprobar:

```bash
git status -sb
git log --oneline --decorate -n 10
```

y confirmar que la rama local ya no está `ahead` del remote.

---

## Prohibiciones Git

Codex NO debe utilizar salvo instrucción explícita del usuario:

```text
git push --force
git push --force-with-lease
git reset --hard
git clean -fd
git rebase -i sobre commits ya publicados
git filter-repo
git filter-branch
```

Tampoco debe:

- borrar ramas remotas ajenas;
- sobrescribir trabajo no relacionado;
- hacer squash automático de historial existente;
- modificar tags publicados;
- cambiar de remote;
- hacer push de secretos;
- hacer commit de `viru.db`;
- hacer commit de `.env`;
- commitear backups locales;
- commitear carpetas temporales de agentes.

---

## Si el push falla

No solucionar a martillazos.

Diagnosticar:

```text
auth failure
non-fast-forward
protected branch
remote changes
CI rejection
pre-push hook
network
```

Para `non-fast-forward`:

1. `git fetch`;
2. inspeccionar commits remotos;
3. integrar de forma segura;
4. re-ejecutar tests afectados;
5. push normal.

Nunca cambiar automáticamente a `--force`.

---

## GitHub debe reflejar el progreso real

Cada fase del roadmap debe dejar una secuencia visible de commits.

Ejemplo:

```text
security(auth): harden Supabase JWT verification
test(auth): add adversarial JWT regression coverage
chore(cutover): remove legacy auth artifacts
docs(cutover): record auth completion proof
```

No esperar al final de toda la modernización para subirlo todo junto.

---

## CI después del push

Si GitHub Actions existe:

Codex debe comprobar que el workflow correspondiente al commit se ha ejecutado correctamente antes de cerrar una fase crítica.

Para fases críticas:

```text
database
auth
RLS
API contract
production build
release
```

un commit local verde pero CI rojo NO es DONE.

Si no se dispone de acceso a GitHub Actions desde el agente:

- registrar esa limitación;
- no fingir que CI está verde;
- dejar el commit/push hecho;
- indicar exactamente qué workflow debe revisarse.

---

## Tags / releases

No crear tag o release automáticamente por cada commit.

Solo para un cierre real de modernización o release de producto.

Ejemplo futuro:

```text
vX.Y.Z
```

requiere:

- staging PASS;
- production gate PASS;
- changelog;
- commit exacto identificado;
- branch remota sincronizada.

---

## Gate GitHub final

Antes de declarar cualquier fase grande `DONE`:

```text
working_tree_clean_or_explained = true
local_commits_unpushed = 0
remote_branch_up_to_date = true
force_push_used = false
secrets_committed = 0
ci_required_checks_green = true | explicitly_unverified
```

Al cierre global de modernización:

```text
git status
```

debe quedar limpio salvo archivos locales deliberadamente ignorados.

Y:

```text
git status -sb
```

no debe mostrar commits locales pendientes de push.

---

## Orden actualizado desde hoy

```text
01. Recontar estado real del repo
02. Revisar y separar el gran diff existente
03. Ejecutar gates
04. Commit por slices coherentes
05. Push a GitHub
06. Confirmar remoto sincronizado
07. Supabase STAGING remoto
08. Commit + push de cada slice validado
09. RLS 30/30
10. Commit + push
11. Auth E2E real
12. Commit + push
13. Orval/TanStack por dominios
14. Commit + push por dominio
15. Staging full gate
16. Commit final de cierre
17. Push
18. Deploy
19. Smoke production
20. Tag/release solo si corresponde
```

**GitHub forma parte del Definition of Done.**
Un cambio que solo existe en el disco del desarrollador no está terminado.


# FASE 1 — PROTEGER Y PUBLICAR EL ESTADO ACTUAL

## Objetivo

Antes de continuar desarrollando, convertir el enorme working tree ya verificado en historial Git recuperable **y subirlo al remote de GitHub de forma segura**.

El peor riesgo actual no es técnico: es perder o mezclar cientos de cambios ya auditados.

## 1.1 Recontar estado actual

Ejecutar y documentar:

```bash
git status --short
git diff --stat
git diff --name-status
git ls-files --others --exclude-standard
```

Guardar en:

```text
docs/post-cutover/pre-commit-state.md
```

Debe incluir:

- HEAD actual;
- rama;
- cantidad de archivos modificados;
- nuevos;
- borrados;
- staged;
- untracked.

## 1.2 Comprobar secretos antes de staging

Verificar:

- `.env`;
- `.env.*`;
- `viru.db`;
- dumps;
- `.pem`;
- `.key`;
- tokens;
- credenciales Supabase;
- JWT secrets;
- connection strings reales.

Ningún secreto debe entrar en Git.

## 1.3 Separar commits por intención

NO crear un único commit de cientos de archivos si puede evitarse.

Orden recomendado:

### Commit A — formatter / mechanical cleanup
Solo Biome, whitespace y ajustes de tests puramente mecánicos.

### Commit B — database / migration authority
Supabase schema, eliminación Alembic, session config, scripts ETL y lockfiles.

### Commit C — auth cutover + security hardening
JWT verification, Supabase auth, fail-fast, tests adversariales y eliminación legacy.

### Commit D — frontend infrastructure
Supabase helpers, Orval, QueryProvider, Zod, shadcn y PostHog.

### Commit E — observability / docs / test hardening
OpenTelemetry, E2E fixes, auditoría, ADRs y documentación.

Si separar rompe el build por dependencias cruzadas, priorizar consistencia y explicar por qué.

## 1.4 Gate antes de publicar

Al final:

```text
backend full suite
frontend full suite
Playwright E2E
typecheck
lint
Biome
api:check
production build
npm audit
```

---

# FASE 2 — CERRAR SUPABASE REMOTO DE VERDAD

Esta es la prioridad técnica más alta.

## 2.1 Crear / seleccionar proyecto STAGING

Debe ser un proyecto de Supabase separado de producción.

Variables separadas:

```text
SUPABASE_STAGING_URL
SUPABASE_STAGING_PUBLISHABLE_KEY
SUPABASE_STAGING_SECRET_KEY
STAGING_DB_URL
```

No commitear valores.

## 2.2 Aplicar migraciones canónicas

Usar únicamente:

```text
supabase/migrations/
```

como autoridad DDL.

Antes:

- confirmar proyecto;
- confirmar que NO es producción;
- revisar SQL;
- dry-run cuando sea posible;
- backup si contiene datos útiles.

## 2.3 Validación de esquema remoto

Comparar STAGING vs baseline esperado:

- tablas;
- columnas;
- tipos;
- PK;
- FK;
- unique;
- checks;
- índices;
- defaults;
- RLS;
- policies.

Generar:

```text
docs/post-cutover/supabase-remote-schema-proof.json
```

Para objetos gobernados por migrations:

```text
schema_drift = 0
```

## 2.4 Matriz RLS REAL de las 30 tablas user-scoped

Crear:

```text
user_a
user_b
```

reales en Supabase Auth STAGING.

Para cada tabla probar según dominio:

```text
A SELECT own
A INSERT own
A UPDATE own
A DELETE own

A SELECT B
A UPDATE B
A DELETE B
A INSERT claiming B

B equivalente

anonymous SELECT
anonymous INSERT
anonymous UPDATE
anonymous DELETE
```

Lo obligatorio:

```text
cross-user bypasses = 0
unexpected anonymous access = 0
```

## 2.5 No probar RLS con bypass

El assertion principal debe usar:

- Supabase client;
- JWT de usuario;
- Data API / rol que respete RLS.

NO:

- postgres superuser;
- service role como usuario;
- conexión privilegiada.

Service role solo para preparar/limpiar fixtures.

## 2.6 Output obligatorio

```text
docs/post-cutover/rls-remote-proof.json
```

Con:

```json
{
  "environment": "staging",
  "tables_expected": 30,
  "tables_tested": 30,
  "cross_user_bypasses": 0,
  "unexpected_anonymous_access": 0,
  "skipped": 0
}
```

Si `tables_tested < tables_expected`, la fase es FAIL.

---

# FASE 3 — VALIDAR AUTH CONTRA SUPABASE REAL

## 3.1 Login real

Probar:

```text
browser
  ↓
Supabase Auth STAGING
  ↓
session
  ↓
frontend
  ↓
FastAPI
  ↓
verify JWT
  ↓
current user
```

Sin mocks.

## 3.2 Resolver definitivamente cookies vs localStorage

Inventariar en `frontend/src`:

```text
localStorage
sessionStorage
sb_access_token
sb_refresh_token
viru_token
viru_refresh_token
```

Clasificar cada uso.

### Objetivo

Debe existir **una sola autoridad de sesión**.

Si la arquitectura Next.js ya tiene helpers SSR, usar Supabase SSR/cookies como camino canónico.

No mantener dos sistemas activos.

### Gate

```text
auth_session_authorities = 1
legacy_session_storage_consumers = 0
```

Si se decide mantener almacenamiento client-side de Supabase de forma intencionada, documentarlo en ADR y demostrar por qué.

## 3.3 Flujos obligatorios

Probar en navegador real:

- register;
- email verification si aplica;
- login;
- reload manteniendo sesión;
- navegación privada;
- logout;
- password recovery;
- sesión expirada;
- token inválido;
- usuario bloqueado/eliminado;
- primer login + provisioning;
- acceso admin sin promoción;
- acceso admin tras promoción explícita.

## 3.4 Admin policy ADR

Crear:

```text
docs/architecture/adr/0004-admin-promotion-policy.md
```

Definir:

- quién puede otorgar admin;
- dónde vive `is_admin`;
- quién NO puede modificarlo;
- promoción;
- revocación;
- auditoría;
- rollback.

Regla:

```text
JWT claim ≠ authority to self-promote
```

---

# FASE 4 — TERMINAR ORVAL + TANSTACK EN PRODUCTO

No asumir que el conteo histórico de consumidores legacy sigue igual: recontar.

## 4.1 Inventario ACTUAL reproducible

Crear:

```text
frontend/scripts/audit-data-access.ts
```

Contar:

- imports de `@/modules/shared/api`;
- `apiFetch`;
- `apiFetchWithStatus`;
- `fetch(`;
- imports de `src/api/generated`;
- `useQuery`;
- `useMutation`;
- `useInfiniteQuery`;
- `useEffect`.

Guardar:

```text
docs/post-cutover/frontend-data-access-baseline.json
```

## 4.2 Clasificar cada call site

```text
QUERY
MUTATION
UPLOAD/DOWNLOAD
STREAMING
SUBSCRIPTION
EXTERNAL_FETCH
UI_EFFECT
BROWSER_EFFECT
SERVER_STATE_EFFECT
DEAD_CODE
```

No convertir a TanStack lo que no sea server state.

## 4.3 Migrar por slices

Orden recomendado:

1. perfil / preferencias / settings;
2. dashboard;
3. watchlists;
4. alerts / notifications;
5. quick search / search al final.

Quick Search va al final por carreras, multi-provider, polling/streaming y estados intermedios.

## 4.4 Patrón obligatorio

Para endpoints FastAPI internos:

```text
FastAPI
  ↓
OpenAPI
  ↓
Orval generated client
  ↓
TanStack Query
  ↓
UI
```

No escribir `fetch("/api/...")` si Orval ya representa el endpoint.

## 4.5 Invalidación

Cada mutation debe declarar:

- query keys afectadas;
- invalidación;
- refetch;
- optimistic update solo si aporta valor.

No usar `window.location.reload()` como sincronización.

## 4.6 DONE

```text
eligible_internal_manual_fetches = 0
eligible_legacy_api_consumers = 0
SERVER_STATE useEffects = 0
```

Pueden existir fetch externos, downloads, SSE/websocket y efectos UI/browser; documentarlos.

---

# FASE 5 — TESTS QUE VALIDAN COMPORTAMIENTO

Durante Biome se descubrió que muchos tests inspeccionaban strings exactos del source.

No crear más tests frágiles así.

Preferir:

```text
render + interaction
HTTP response
DB state
visible UI
network call
authorization result
generated contract
```

sobre:

```text
expect(source).toContain("exact formatting")
```

Para tests estáticos, normalizar whitespace o usar AST cuando merezca la pena.

## E2E de auth

Nunca volver a aceptar una aserción débil tipo:

```text
main is visible
```

porque el login también puede tener `<main>`.

Comprobar algo exclusivo:

- identidad;
- heading privado;
- URL no `/login`;
- navegación privada;
- API protegida exitosa.

---

# FASE 6 — OBSERVABILIDAD REMOTA

## OpenTelemetry

En STAGING realizar una búsqueda real y demostrar una trace:

```text
HTTP request
FastAPI
search orchestration
provider calls
database
response
```

Verificar que no aparezcan:

```text
password
authorization
JWT
secret
PII sensible
```

Guardar:

```text
docs/post-cutover/otel-staging-proof.md
```

## PostHog

Ejecutar:

```text
login
search
watchlist add
watchlist remove
alert create
logout
```

Verificar:

- eventos correctos;
- no PII;
- replay masked;
- reset al logout;
- identidad estable;
- sin eventos duplicados.

---

# FASE 7 — LIMPIEZA FINAL DE DEUDA DE MIGRACIÓN

Buscar:

```text
MIGRATION_STATUS
PARTIAL
SHADOW_VERIFIED
EXPERIMENTAL_ONLY
TODO migration
legacy
temporary bridge
fallback
deprecated
```

Clasificar:

```text
HISTORICAL_DOC
ACTIVE_DEBT
DEAD_CODE
VALID_COMPATIBILITY
```

Eliminar si realmente está muerto:

- scripts one-shot ya inútiles;
- adapters legacy;
- auth bridge;
- fixtures antiguas;
- referencias a Alembic;
- referencias a Docker;
- documentación que presente SQLite como runtime;
- proofs falsos/superados.

Mover histórico útil a:

```text
docs/history/migration/
```

---

# FASE 8 — STAGING → PRODUCCIÓN

## Checklist STAGING

```text
[ ] schema remote exact
[ ] migrations clean
[ ] RLS 30/30
[ ] cross-user bypass = 0
[ ] auth real E2E
[ ] no legacy auth path
[ ] backend full tests
[ ] frontend full tests
[ ] E2E
[ ] typecheck
[ ] lint
[ ] biome
[ ] api:check
[ ] build
[ ] npm audit
[ ] OTel proof
[ ] PostHog proof
```

## Backup

Antes de producción:

- backup DB;
- export config relevante;
- commit/version exacta;
- rollback documentado.

## Deploy

Deploy del commit exacto validado en STAGING.

No modificar código entre staging-verificado y producción.

## Smoke test producción

- landing;
- login;
- authenticated endpoint;
- search;
- watchlist read;
- logout;
- health;
- logs;
- trace básica.

---

# FASE 9 — CIERRE FORMAL

Crear:

```text
docs/post-cutover/FINAL_MODERNIZATION_CLOSURE.md
```

Solo PASS si:

```text
Docker runtime dependencies       0
SQLite runtime fallback           0
Alembic migration authority       0
DB authorities                    1
Auth authorities                  1
RLS remote tables                 30/30
RLS cross-user bypasses           0
critical skipped remote tests     0

OpenAPI drift                     0
eligible legacy API consumers     0
eligible server-state effects     0

TypeScript errors                 0
Backend test failures             0
Frontend test failures            0
E2E failures                      0
Production build                  PASS
Critical dependency vulns         0
Local commits pending push         0
Remote branch up to date           YES
Required GitHub CI checks          PASS
```

No usar `PASS_WITH_DEFERRED_ITEMS` para requisitos críticos.

---

# FASE 10 — PARAR DE MODERNIZAR

Cuando la fase 9 sea PASS:

**STOP.**

No:

- rehacer FastAPI;
- sustituir Supabase;
- migrar Next.js a Vite;
- añadir microservicios;
- meter Valkey/Typesense/Temporal/Trigger.dev por moda.

La arquitectura tiene que empezar a amortizarse.

---

# DESARROLLO NORMAL DE FEATURES

A partir de aquí, por feature:

```text
1. Supabase migration si cambia datos
2. SQLAlchemy model si backend lo necesita
3. FastAPI/Pydantic
4. OpenAPI
5. regenerate Orval
6. TanStack Query
7. Zod en fronteras no confiables
8. shadcn/primitivas existentes
9. tests
10. Playwright journey
11. observability
```

---

# QUALITY GATE ESTÁNDAR PARA CODEX

## Frontend normal

```text
Biome
ESLint si sigue activo
Typecheck
tests afectados
Playwright afectado
build si routing/config
```

## Backend normal

```text
pytest afectado
OpenAPI contract
auth/permission tests si aplica
```

## Full-stack

```text
backend tests relevantes
frontend tests relevantes
api:check
typecheck
Playwright journey
```

## Release

```text
full backend
full frontend
full E2E
typecheck
lint
biome
api:check
build
dependency audit
```

---

# TECNOLOGÍAS OPCIONALES — SOLO CON EVIDENCIA

## Valkey
Solo si hay cache/locks/singleflight distribuido mediblemente necesarios.

## Typesense
Solo si el catálogo/PostgreSQL deja de cumplir latencia o relevancia.

## Trigger.dev / Temporal
No mientras los workers Python actuales sean fiables, observables y no pierdan jobs.

---

# ANTI-SLOP RULES PERMANENTES

1. **Search before create.**
2. **One authority per concern.**
3. **Generated means generated.**
4. **No fallback infrastructure.**
5. **No secret defaults.**
6. **No auth magic.**
7. **Tests prove behavior.**
8. **No PASS from partial commands.**
9. **Recount after refactor.**
10. **Delete replaced legacy code only after 0 consumers.**

Autoridades:

```text
DB              Supabase PostgreSQL
Schema          supabase/migrations
API contract    OpenAPI
Generated API   Orval
Server state    TanStack Query
Auth            Supabase Auth
```

---

# ORDEN EXACTO RECOMENDADO DESDE HOY

```text
01. Freeze + review final del diff actual
02. Commit/publish del estado hardenizado
03. Supabase STAGING remoto
04. Remote schema validation
05. RLS 30/30
06. Auth E2E real + una sola session authority
07. Admin promotion ADR
08. OTel/PostHog runtime proof
09. Cerrar slices SHADOW_VERIFIED
10. Migrar frontend legacy API → Orval/TanStack por dominios
11. Eliminar consumidores legacy al llegar a 0
12. Staging full gate
13. Production deploy + smoke
14. FINAL_MODERNIZATION_CLOSURE.md
15. STOP architecture work
16. volver a features de Viru
```

---

# PRIMERA TAREA PARA EL SIGUIENTE CODEX

> Revisa el estado actual del repositorio después del hardening final.
> Recuenta Git, auth storage, consumidores del cliente API legacy,
> imports de Orval/TanStack, referencias a SQLite/Alembic/Docker y
> estado de los slices SHADOW_VERIFIED.
> Ejecuta los gates rápidos y genera `docs/post-cutover/CURRENT_STATE.md`.
> Después prepara un proyecto Supabase STAGING remoto y ejecuta la
> validación de schema + matriz RLS, sin Docker y sin tocar producción.
> No declares PASS con tests skipped ni con credenciales ausentes.

---

# DEFINITION OF SUCCESS

```text
VIRU

Next.js / React
├── shadcn/ui
├── TanStack Query
├── Zod
└── Orval generated API
        │
      OpenAPI
        │
     FastAPI
├── search
├── providers
├── pricing
├── recommendations
└── workers
        │
Supabase
├── Auth
├── PostgreSQL
├── RLS
├── Realtime (solo donde se use)
└── Storage (solo donde se use)

Quality:
Biome
Typecheck
Tests
Playwright
Observability
```

Con:

```text
1 DB authority
1 auth authority
1 API contract
1 generated client path
0 silent fallbacks
0 critical skipped security tests
0 fake green proofs
```

Cuando esto esté demostrado en STAGING y producción, la modernización termina.

A partir de ahí la prioridad vuelve a ser **hacer Viru mejor**, no seguir reconstruyendo su infraestructura.
