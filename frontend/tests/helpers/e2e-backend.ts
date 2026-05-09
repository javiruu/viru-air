import fs from "node:fs";
import path from "node:path";
import { spawn, type ChildProcess } from "node:child_process";

const API_BASE = process.env.E2E_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
const FRONTEND_BASE = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
const BACKEND_BASE = API_BASE.replace(/\/api\/v1\/?$/, "");
const BACKEND_HEALTH_URL = `${BACKEND_BASE}/health`;
const FRONTEND_HEALTH_URL = FRONTEND_BASE;
const BACKEND_START_TIMEOUT_MS = Number(process.env.E2E_BACKEND_START_TIMEOUT_MS || "45000");
const FRONTEND_START_TIMEOUT_MS = Number(process.env.E2E_FRONTEND_START_TIMEOUT_MS || "90000");

let backendProcess: ChildProcess | null = null;
let frontendProcess: ChildProcess | null = null;
let shutdownHookRegistered = false;
let backendUnavailable = false;
let frontendUnavailable = false;

async function waitForBackendHealth(timeoutMs: number): Promise<boolean> {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(BACKEND_HEALTH_URL, { method: "GET" });
      if (response.ok) {
        return true;
      }
    } catch {
      // Backend not ready yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

async function waitForFrontendReady(timeoutMs: number): Promise<boolean> {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(FRONTEND_HEALTH_URL, { method: "GET" });
      if (response.ok) {
        return true;
      }
    } catch {
      // Frontend not ready yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 800));
  }
  return false;
}

function resolveBackendPythonPath() {
  if (process.env.E2E_BACKEND_PYTHON && process.env.E2E_BACKEND_PYTHON.trim()) {
    return process.env.E2E_BACKEND_PYTHON.trim();
  }
  return path.resolve(process.cwd(), "../backend/.venv/Scripts/python.exe");
}

function ensureShutdownHook() {
  if (shutdownHookRegistered) {
    return;
  }
  shutdownHookRegistered = true;
  process.on("exit", () => {
    if (backendProcess && !backendProcess.killed) {
      backendProcess.kill("SIGTERM");
    }
    if (frontendProcess && !frontendProcess.killed) {
      frontendProcess.kill("SIGTERM");
    }
  });
}

function startBackendProcess() {
  if (backendProcess && !backendProcess.killed) {
    return;
  }

  const pythonPath = resolveBackendPythonPath();
  if (!fs.existsSync(pythonPath)) {
    throw new Error(`backend_python_not_found:${pythonPath}`);
  }

  const backendCwd = path.resolve(process.cwd(), "../backend");
  backendProcess = spawn(
    pythonPath,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    {
      cwd: backendCwd,
      stdio: "ignore",
      windowsHide: true,
    },
  );
  backendProcess.unref();
  ensureShutdownHook();
}

function startFrontendProcess() {
  if (frontendProcess && !frontendProcess.killed) {
    return;
  }
  const frontendCwd = process.cwd();
  const comspec = process.env.ComSpec || "cmd.exe";
  frontendProcess = spawn(
    comspec,
    ["/c", "npm.cmd run dev"],
    {
      cwd: frontendCwd,
      stdio: "ignore",
      windowsHide: true,
    },
  );
  frontendProcess.unref();
  ensureShutdownHook();
}

export async function ensureBackendReady(): Promise<void> {
  if (backendUnavailable) {
    throw new Error("backend_unavailable_cached");
  }
  if (await waitForBackendHealth(1500)) {
    return;
  }
  startBackendProcess();
  const healthy = await waitForBackendHealth(BACKEND_START_TIMEOUT_MS);
  if (!healthy) {
    backendUnavailable = true;
    throw new Error(`backend_health_timeout:${BACKEND_HEALTH_URL}`);
  }
}

export async function ensureFrontendReady(): Promise<void> {
  if (frontendUnavailable) {
    throw new Error("frontend_unavailable_cached");
  }
  if (await waitForFrontendReady(2000)) {
    return;
  }
  startFrontendProcess();
  const ready = await waitForFrontendReady(FRONTEND_START_TIMEOUT_MS);
  if (!ready) {
    frontendUnavailable = true;
    throw new Error(`frontend_ready_timeout:${FRONTEND_HEALTH_URL}`);
  }
}

export async function ensureE2EAppReady(): Promise<void> {
  await ensureBackendReady();
  await ensureFrontendReady();
}

export async function createSessionToken(): Promise<string> {
  await ensureBackendReady();
  const email = `codex-e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  const password = "Test123456!";
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw new Error(`register_failed_${response.status}`);
  }
  const auth = (await response.json()) as { access_token?: string };
  if (!auth.access_token) {
    throw new Error("register_missing_token");
  }
  return auth.access_token;
}
