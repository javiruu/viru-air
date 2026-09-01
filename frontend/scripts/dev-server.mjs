import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DEFAULT_PORT = 3000;
const SERVER_READY_TIMEOUT_MS = 5 * 60_000;
const ROUTE_REQUEST_TIMEOUT_MS = 120_000;
const ROUTE_PAUSE_MS = 75;
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

export function isRouteWarmupEnabled(environment) {
  const configuredValue = environment.VIRU_ROUTE_WARMUP?.trim().toLowerCase();
  return configuredValue !== "0" && configuredValue !== "false";
}

function delay(milliseconds) {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
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
    await delay(250);
  }
  return false;
}

export async function warmStaticRoutes({
  origin,
  routes,
  pauseMs = ROUTE_PAUSE_MS,
  requestTimeoutMs = ROUTE_REQUEST_TIMEOUT_MS,
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
    if (pauseMs > 0 && index < routes.length - 1) await delay(pauseMs);
  }

  return { total: routes.length, succeeded, failed };
}

async function runRouteWarmup({ origin, appDirectory, signal }) {
  const routes = await discoverStaticRoutes(appDirectory);
  console.log(`[Viru warmup] ${routes.length} rutas estáticas descubiertas; esperando a Next...`);
  const serverReady = await waitForServer(origin, signal);
  if (!serverReady) {
    if (!signal.aborted) console.warn("[Viru warmup] Next no respondió a tiempo; se omite el calentamiento.");
    return;
  }

  const queuedRoutes = routes.filter((route) => route !== "/");
  console.log(`[Viru warmup] Portada lista; compilando ${queuedRoutes.length} rutas en segundo plano.`);
  const summary = await warmStaticRoutes({ origin, routes: queuedRoutes, signal });
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

  if (isRouteWarmupEnabled(process.env)) {
    void runRouteWarmup({
      origin,
      appDirectory: path.resolve("src", "app"),
      signal: abortController.signal,
    }).catch((error) => {
      const reason = error instanceof Error ? error.message : "error desconocido";
      console.warn(`[Viru warmup] No se pudo completar: ${reason}`);
    });
  } else {
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
