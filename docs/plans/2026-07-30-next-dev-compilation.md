# Next.js Development Compilation Implementation Plan

> **For Codex:** Execute this plan task-by-task in the canonical repository and commit directly to `main`.

**Goal:** Start the Next.js frontend faster and compile every static App Router page automatically in a controlled background queue.

**Architecture:** Replace the redundant Webpack-only alias with the existing TypeScript path mapping, run Next 15.5 with Turbopack, and place a small Node supervisor in front of `next dev`. The supervisor discovers static `page.tsx` routes, waits for the root route, then warms each remaining route sequentially without affecting production commands.

**Tech Stack:** Next.js 15.5, Node.js ESM, App Router, Node test runner, Playwright/Chrome.

---

### Task 1: Capture a reproducible baseline

**Files:**

- Read: `frontend/package.json`
- Read: `frontend/next.config.js`
- Read: `frontend/src/app/**/page.tsx`

**Step 1: Inventory the routes**

List all `page.tsx` files and classify route groups, static routes, dynamic
segments and parallel slots.

**Step 2: Measure Webpack development behavior**

Start an isolated copy of the current frontend on an unused port, request `/`,
`/watchlist`, `/quick-search` and the complete static route set, and record:

- time until `/` responds;
- first-request time per route;
- total warmup time;
- compiler reported by Next.

**Step 3: Preserve evidence outside the repository**

Keep raw temporary logs outside the worktree and report only summarized,
non-sensitive measurements.

### Task 2: Test route discovery and CLI parsing

**Files:**

- Create: `frontend/tests/dev-server.test.mjs`
- Create: `frontend/scripts/dev-server.mjs`

**Step 1: Write failing tests**

Cover:

```js
discoverStaticRoutes(appDirectory)
resolveDevPort(commandArguments)
isRouteWarmupEnabled(environment)
```

Expected route behavior:

- `(private)/watchlist/page.tsx` becomes `/watchlist`;
- `(public)/page.tsx` becomes `/`;
- dynamic segments, route handlers and parallel slots are excluded;
- duplicates are removed;
- primary Viru routes appear before the deterministic remainder;
- `-p`, `--port` and `--port=<value>` resolve consistently.

**Step 2: Run the tests and confirm RED**

Run:

```bash
cd frontend
node --test tests/dev-server.test.mjs
```

Expected: FAIL because `scripts/dev-server.mjs` does not exist.

**Step 3: Implement pure helpers**

Add strict ESM helpers using only Node built-ins. Keep filesystem discovery,
path normalization, CLI parsing and environment parsing independent from
process spawning so they remain deterministic under test.

**Step 4: Run the tests and confirm GREEN**

Run the same targeted command and expect all cases to pass.

### Task 3: Implement the supervised Turbopack server

**Files:**

- Modify: `frontend/scripts/dev-server.mjs`
- Modify: `frontend/package.json`
- Modify: `frontend/next.config.js`

**Step 1: Add the warmup behavior**

The entrypoint will:

```js
const child = spawn(process.execPath, [
  nextCli,
  "dev",
  "--turbopack",
  "-p",
  "3000",
  ...forwardedArguments,
], { stdio: "inherit", env: process.env });

void warmDevelopmentRoutes({
  origin,
  routes,
  timeoutMs,
  signal,
});
```

The warmup will wait for `/`, then fetch routes sequentially with a timeout,
consume every response body, log compact progress, and isolate failures by
route. It will skip entirely when `VIRU_ROUTE_WARMUP=0`.

**Step 2: Switch the development command**

Change `npm run dev` to execute the supervisor. Leave `build` and `start`
unchanged.

**Step 3: Remove the redundant Webpack alias**

Delete the `path` import and `webpack` callback from `next.config.js`.
Retain rewrites and `reactStrictMode`.

**Step 4: Re-run targeted tests**

Expected: route discovery, CLI parsing and warmup environment tests pass.

### Task 4: Verify compatibility and observable behavior

**Files:**

- Test: `frontend/tests/dev-server.test.mjs`
- Verify: `frontend/package.json`
- Verify: `frontend/next.config.js`

**Step 1: Static checks**

Run:

```bash
cd frontend
npx tsc --noEmit
npm test
npm run build
```

Expected: exit code 0, or unrelated pre-existing failures documented
separately with evidence.

**Step 2: Development runtime**

Run `npm run dev -- --port 3020`, verify:

- Next reports Turbopack;
- `/` becomes available without waiting for the whole route set;
- the background log discovers all static routes;
- the queue completes with controlled concurrency;
- disabling via `VIRU_ROUTE_WARMUP=0` suppresses the queue.

**Step 3: Browser QA**

Open `/`, `/watchlist`, `/quick-search`, `/hoteles`, `/preferencias` and
`/admin` in real Chrome. Verify successful navigation, no new compilation
pause after warmup, and no browser console errors caused by the change.

**Step 4: Compare before and after**

Repeat the isolated measurements and report startup, total warmup and
post-warm route latency. Do not claim a gain that is not present in the
observed numbers.

### Task 5: Review and publish

**Files:**

- Update when warranted: `HISTORY.md`
- Review all intended files

**Step 1: Runtime debugging audit**

Test three hypotheses with evidence:

1. route discovery misses or invents pages;
2. the warmup blocks or crashes Next;
3. Turbopack breaks aliases or production build compatibility.

**Step 2: Review**

Run the required goal, QA, code, security and context review lanes. Fix every
blocking finding and rerun affected verification.

**Step 3: Commit**

Stage only the implementation, tests and directly related documentation.
Use a conventional commit matching repository history.

**Step 4: Push**

Push `main` to its configured upstream and confirm the remote update.
