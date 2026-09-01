import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DEFAULT_PORT = 3000;
const SERVER_READY_TIMEOUT_MS = 5 * 60_000;
const ROUTE_REQUEST_TIMEOUT_MS = 120_000;
const FAST_ROUTE_PAUSE_MS = 75;
const SLOW_WARMUP_PROFILE = Object.freeze({
  mode: "slow",
  initialDelayMs: 8_000,
  pauseMs: 1_500,
  batchSize: 2,
  batchPauseMs: 4_000,
});
const FAST_WARMUP_PROFILE = Object.freeze({
  mode: "fast",
  initialDelayMs: 0,
  pauseMs: FAST_ROUTE_PAUSE_MS,
  batchSize: Number.POSITIVE_INFINITY,
  batchPauseMs: 0,
});
const PRIMARY_ROUTES = [
  "/",
  "/dashboard",
  "/quick-search",
  "/watchlist",
  "/history",
  "/alerts",
  "/hoteles",
  "/puerta-a-puerta",
  "/recomendaciones",
  "/notifications",
];

function routePriority(route) {
  const primaryIndex = PRIMARY_ROUTES.indexOf(route);
  return primaryIndex === -1 ? PRIMARY_ROUTES.length : primaryIndex;
}

async function findPageFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nestedFiles = await Promise.all(
    entries.map(async (entry) => {
      const entryPath = path.join(directory, entry.name);
      if (entry.isDirectory()) return findPageFiles(entryPath);
      return entry.isFile() && entry.name === "page.tsx" ? [entryPath] : [];
    }),
  );
  return nestedFiles.flat();
}

function routeFromPageFile(appDirectory, pageFile) {
  const segments = path.relative(appDirectory, path.dirname(pageFile)).split(path.sep).filter(Boolean);
  if (segments.some((segment) => segment.startsWith("@") || segment.startsWith("["))) return null;

  const urlSegments = segments.filter((segment) => !segment.startsWith("("));
  if (urlSegments[0] === "api") return null;
  return urlSegments.length === 0 ? "/" : `/${urlSegments.join("/")}`;
}

export async function discoverStaticRoutes(appDirectory) {
  const pageFiles = await findPageFiles(appDirectory);
  const routes = new Set(
    pageFiles
      .map((pageFile) => routeFromPageFile(appDirectory, pageFile))
      .filter((route) => route !== null),
  );

  return [...routes].sort((left, right) => {
    const priorityDifference = routePriority(left) - routePriority(right);
    return priorityDifference === 0 ? left.localeCompare(right) : priorityDifference;
  });
}

function parsePort(value) {
  const parsed = Number.parseInt(value, 10);
  return Number.isInteger(parsed) && parsed > 0 && parsed <= 65_535 ? parsed : null;
}

export function resolveDevDistDir(environment = process.env, port = DEFAULT_PORT) {
  const configuredDir = environment.NEXT_DIST_DIR?.trim();
  if (configuredDir) return configuredDir;
  return `.next-dev-${port}`;
}

export function resolveDevPort(commandArguments) {
  let port = DEFAULT_PORT;
  for (let index = 0; index < commandArguments.length; index += 1) {
    const argument = commandArguments[index];
    if (argument === "-p" || argument === "--port") {
      const parsed = parsePort(commandArguments[index + 1] ?? "");
      if (parsed !== null) port = parsed;
      index += 1;
      continue;
    }
    if (argument.startsWith("--port=")) {
      const parsed = parsePort(argument.slice("--port=".length));
      if (parsed !== null) port = parsed;
    }
  }
  return port;
}

export function buildNextDevArguments(commandArguments) {
  const forwardedArguments = [];
  for (let index = 0; index < commandArguments.length; index += 1) {
    const argument = commandArguments[index];
    if (argument === "--warmup" || argument.startsWith("--warmup=")) continue;
    if (argument === "-p" || argument === "--port") {
      index += 1;
      continue;
    }
    if (argument.startsWith("--port=")) continue;
    forwardedArguments.push(argument);
  }

  const port = resolveDevPort(commandArguments);
  return [
    "dev",
    "--turbopack",
    "-p",
    String(port),
    ...forwardedArguments,
  ];
}

function getCommandWarmupMode(commandArguments) {
  for (const argument of commandArguments) {
    if (argument === "--warmup") return "slow";
    if (argument.startsWith("--warmup=")) return argument.slice("--warmup=".length).trim().toLowerCase();
  }
  return undefined;
}

export function resolveRouteWarmupProfile(environment = process.env, commandArguments = []) {
  const configuredMode = environment.VIRU_ROUTE_WARMUP?.trim().toLowerCase();
  const mode = configuredMode === undefined ? getCommandWarmupMode(commandArguments) ?? "slow" : configuredMode;

  if (["0", "false", "off", "none"].includes(mode)) return null;
  if (["fast", "eager"].includes(mode)) return { ...FAST_WARMUP_PROFILE };
  if (["1", "true", "slow"].includes(mode)) return { ...SLOW_WARMUP_PROFILE };
  return null;
}

export function isRouteWarmupEnabled(environment, commandArguments = []) {
  return resolveRouteWarmupProfile(environment, commandArguments) !== null;
}

function delay(milliseconds, signal) {
  if (milliseconds <= 0 || signal?.aborted) return Promise.resolve();
  return new Promise((resolve) => {
    const finish = () => {
      clearTimeout(timeout);
      signal?.removeEventListener("abort", finish);
      resolve();
    };
    const timeout = setTimeout(finish, milliseconds);
    signal?.addEventListener("abort", finish, { once: true });
  });
}

function routePauseAfter({ index, total, pauseMs, batchSize, batchPauseMs }) {
  if (index >= total - 1) return 0;
  const completed = index + 1;
  const endsBatch = Number.isFinite(batchSize) && batchSize > 0 && completed % batchSize === 0;
  return endsBatch ? batchPauseMs : pauseMs;
}

async function requestRoute(origin, route, timeoutMs, parentSignal) {
  const requestController = new AbortController();
  const abortRequest = () => requestController.abort();
  const timeout = setTimeout(abortRequest, timeoutMs);

  if (parentSignal?.aborted) abortRequest();
  else parentSignal?.addEventListener("abort", abortRequest, { once: true });

  try {
    const response = await fetch(new URL(route, origin), {
      headers: { accept: "text/html" },
      redirect: "manual",
      signal: requestController.signal,
    });
    await response.arrayBuffer();
    return response.status;
  } finally {
    clearTimeout(timeout);
    parentSignal?.removeEventListener("abort", abortRequest);
  }
}

async function waitForServer(origin, signal) {
  const startedAt = Date.now();
  while (!signal.aborted && Date.now() - startedAt < SERVER_READY_TIMEOUT_MS) {
    try {
      const status = await requestRoute(origin, "/", 5_000, signal);
      if (status < 500) return true;
    } catch (error) {
      if (signal.aborted) return false;
      if (!(error instanceof Error)) throw error;
    }
    await delay(250, signal);
  }
  return false;
}

export async function warmStaticRoutes({
  origin,
  routes,
  pauseMs = FAST_ROUTE_PAUSE_MS,
  batchSize = Number.POSITIVE_INFINITY,
  batchPauseMs = 0,
  requestTimeoutMs = ROUTE_REQUEST_TIMEOUT_MS,
  delayFn = delay,
  log = console.log,
  signal,
}) {
  const failed = [];
  let succeeded = 0;

  for (const [index, route] of routes.entries()) {
    if (signal?.aborted) break;
    const startedAt = Date.now();
    try {
      const status = await requestRoute(origin, route, requestTimeoutMs, signal);
      const elapsedMs = Date.now() - startedAt;
      if (status >= 500) {
        failed.push(route);
        log(`[Viru warmup] ${index + 1}/${routes.length} ${route} HTTP ${status} (${elapsedMs} ms)`);
      } else {
        succeeded += 1;
        log(`[Viru warmup] ${index + 1}/${routes.length} ${route} lista (${elapsedMs} ms)`);
      }
    } catch (error) {
      if (signal?.aborted) break;
      failed.push(route);
      const reason = error instanceof Error ? error.message : "error desconocido";
      log(`[Viru warmup] ${index + 1}/${routes.length} ${route} falló: ${reason}`);
    }

    const nextPauseMs = routePauseAfter({ index, total: routes.length, pauseMs, batchSize, batchPauseMs });
    if (nextPauseMs > 0) await delayFn(nextPauseMs, signal);
  }

  return { total: routes.length, succeeded, failed };
}

async function runRouteWarmup({ origin, appDirectory, profile, signal }) {
  const routes = await discoverStaticRoutes(appDirectory);
  console.log(`[Viru warmup] ${routes.length} rutas estáticas descubiertas; modo ${profile.mode}; esperando a Next...`);
  const serverReady = await waitForServer(origin, signal);
  if (!serverReady) {
    if (!signal.aborted) console.warn("[Viru warmup] Next no respondió a tiempo; se omite el calentamiento.");
    return;
  }

  const queuedRoutes = routes.filter((route) => route !== "/");
  if (profile.initialDelayMs > 0) {
    console.log(`[Viru warmup] Portada lista; cediendo ${profile.initialDelayMs / 1_000} s antes de la primera tanda.`);
    await delay(profile.initialDelayMs, signal);
    if (signal.aborted) return;
  }

  console.log(
    `[Viru warmup] Compilando ${queuedRoutes.length} rutas en segundo plano: ${profile.batchSize} rutas por tanda, ${profile.pauseMs} ms entre rutas y ${profile.batchPauseMs} ms entre tandas.`,
  );
  const summary = await warmStaticRoutes({
    origin,
    routes: queuedRoutes,
    pauseMs: profile.pauseMs,
    batchSize: profile.batchSize,
    batchPauseMs: profile.batchPauseMs,
    signal,
  });
  const suffix = summary.failed.length === 0 ? "" : `; fallaron: ${summary.failed.join(", ")}`;
  console.log(`[Viru warmup] Completado: ${summary.succeeded}/${summary.total} rutas${suffix}.`);
}

async function runDevelopmentServer(commandArguments) {
  const require = createRequire(import.meta.url);
  const nextCli = require.resolve("next/dist/bin/next");
  const port = resolveDevPort(commandArguments);
  const origin = `http://127.0.0.1:${port}`;
  const environment = {
    ...process.env,
    NEXT_DIST_DIR: resolveDevDistDir(process.env, port),
  };
  const abortController = new AbortController();
  const nextProcess = spawn(
    process.execPath,
    [nextCli, ...buildNextDevArguments(commandArguments)],
    { env: environment, stdio: "inherit" },
  );
  const warmupProfile = resolveRouteWarmupProfile(process.env, commandArguments);

  if (warmupProfile) {
    void runRouteWarmup({
      origin,
      appDirectory: path.resolve("src", "app"),
      profile: warmupProfile,
      signal: abortController.signal,
    }).catch((error) => {
      const reason = error instanceof Error ? error.message : "error desconocido";
      console.warn(`[Viru warmup] No se pudo completar: ${reason}`);
    });
  } else if (process.env.VIRU_ROUTE_WARMUP) {
    console.log("[Viru warmup] Desactivado mediante VIRU_ROUTE_WARMUP.");
  }

  await new Promise((resolve, reject) => {
    nextProcess.once("error", reject);
    nextProcess.once("exit", (code) => {
      abortController.abort();
      process.exitCode = code ?? 1;
      resolve();
    });
  });
}

const isMainModule =
  typeof process.argv[1] === "string" &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isMainModule) {
  try {
    await runDevelopmentServer(process.argv.slice(2));
  } catch (error) {
    const reason = error instanceof Error ? error.message : "error desconocido";
    console.error(`[Viru dev] No se pudo arrancar Next: ${reason}`);
    process.exitCode = 1;
  }
}
