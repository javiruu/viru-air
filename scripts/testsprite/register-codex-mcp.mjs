#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const MIN_NODE_MAJOR = 22;
const SERVER_NAME = "TestSprite";
const EXPECTED_COMMAND = "npx";
const EXPECTED_PACKAGE = "@testsprite/testsprite-mcp@latest";

function fail(message) {
  console.error(`[testsprite-bootstrap] ${message}`);
  process.exit(1);
}

function getExecutableCandidates(command) {
  if (process.platform !== "win32") {
    return [command];
  }

  return [command];
}

function quoteForPowerShell(arg) {
  return `'${String(arg).replace(/'/g, "''")}'`;
}

function runWindowsCommand(command, args) {
  return spawnSync(
    "powershell.exe",
    [
      "-NoProfile",
      "-Command",
      ["&", quoteForPowerShell(command), ...args.map(quoteForPowerShell)].join(" "),
    ],
    {
      encoding: "utf8",
      stdio: "pipe",
    },
  );
}

function runCommand(command, args, { allowFailure = false } = {}) {
  let lastResult = null;

  for (const candidate of getExecutableCandidates(command)) {
    const result =
      process.platform === "win32"
        ? runWindowsCommand(candidate, args)
        : spawnSync(candidate, args, {
            encoding: "utf8",
            stdio: "pipe",
          });

    if (
      result.error &&
      (result.error.code === "ENOENT" ||
        result.error.code === "EPERM" ||
        result.error.code === "EINVAL")
    ) {
      lastResult = result;
      continue;
    }

    if (result.error) {
      fail(`No se pudo ejecutar '${candidate}': ${result.error.message}`);
    }

    if (result.status !== 0 && !allowFailure) {
      const stderr = (result.stderr || "").trim();
      const stdout = (result.stdout || "").trim();
      fail(
        [
          `El comando '${candidate} ${args.join(" ")}' ha fallado con codigo ${result.status}.`,
          stderr || stdout,
        ]
          .filter(Boolean)
          .join("\n"),
      );
    }

    return result;
  }

  if (allowFailure && lastResult) {
    return lastResult;
  }

  fail(`No se encontro el ejecutable '${command}' en PATH.`);
}

function ensureNodeVersion() {
  const [majorText] = process.versions.node.split(".");
  const major = Number.parseInt(majorText, 10);

  if (Number.isNaN(major) || major < MIN_NODE_MAJOR) {
    fail(
      `Node.js ${MIN_NODE_MAJOR}+ es obligatorio. Version detectada: ${process.version}.`,
    );
  }
}

function loadRepoConfig(repoRoot) {
  const mcpConfigPath = path.join(repoRoot, "mcp.json");
  let parsed;

  try {
    parsed = JSON.parse(fs.readFileSync(mcpConfigPath, "utf8"));
  } catch (error) {
    fail(`No se pudo leer ${mcpConfigPath}: ${error.message}`);
  }

  const server = parsed?.mcpServers?.[SERVER_NAME];
  if (!server || typeof server !== "object") {
    fail(`mcp.json debe definir mcpServers.${SERVER_NAME}.`);
  }

  if (server.command !== EXPECTED_COMMAND) {
    fail(
      `mcp.json debe usar command='${EXPECTED_COMMAND}' para ${SERVER_NAME}.`,
    );
  }

  if (!Array.isArray(server.args) || server.args.length === 0) {
    fail(`mcp.json debe incluir args no vacios para ${SERVER_NAME}.`);
  }

  if (!server.args.includes(EXPECTED_PACKAGE)) {
    fail(
      `mcp.json debe incluir '${EXPECTED_PACKAGE}' en args para ${SERVER_NAME}.`,
    );
  }

  const apiKey = server?.env?.API_KEY;
  if (typeof apiKey !== "string" || apiKey.trim() === "") {
    fail(`mcp.json debe incluir env.API_KEY para ${SERVER_NAME}.`);
  }

  return {
    command: server.command,
    args: server.args,
    apiKey,
    mcpConfigPath,
  };
}

function getExistingServer() {
  const result = runCommand("codex", ["mcp", "get", SERVER_NAME, "--json"], {
    allowFailure: true,
  });

  if (result.status !== 0) {
    return null;
  }

  try {
    return JSON.parse(result.stdout);
  } catch (error) {
    fail(
      `No se pudo parsear la salida JSON de 'codex mcp get ${SERVER_NAME} --json': ${error.message}`,
    );
  }
}

function registerServer(serverConfig) {
  const existingServer = getExistingServer();
  const hadExistingServer = existingServer !== null;

  if (hadExistingServer) {
    runCommand("codex", ["mcp", "remove", SERVER_NAME]);
  }

  runCommand("codex", [
    "mcp",
    "add",
    SERVER_NAME,
    "--env",
    `API_KEY=${serverConfig.apiKey}`,
    "--",
    serverConfig.command,
    ...serverConfig.args,
  ]);

  const registered = getExistingServer();
  if (!registered) {
    fail(`No se pudo verificar la configuracion final de ${SERVER_NAME}.`);
  }

  return {
    hadExistingServer,
    registered,
  };
}

function assertRegisteredConfig(registered, serverConfig) {
  const command = registered?.transport?.command;
  const args = registered?.transport?.args;
  const envApiKey = registered?.transport?.env?.API_KEY;

  if (command !== serverConfig.command) {
    fail(
      `La configuracion registrada usa command='${command}' en vez de '${serverConfig.command}'.`,
    );
  }

  if (!Array.isArray(args) || args.join("\u0000") !== serverConfig.args.join("\u0000")) {
    fail(`La configuracion registrada no conserva los args esperados.`);
  }

  if (envApiKey !== serverConfig.apiKey) {
    fail(`La configuracion registrada no conserva env.API_KEY.`);
  }
}

function main() {
  ensureNodeVersion();

  const scriptPath = fileURLToPath(import.meta.url);
  const scriptDir = path.dirname(scriptPath);
  const repoRoot = path.resolve(scriptDir, "..", "..");
  const serverConfig = loadRepoConfig(repoRoot);

  const listBefore = runCommand("codex", ["mcp", "list"], { allowFailure: false });
  const hadListedServer = (listBefore.stdout || "").includes(SERVER_NAME);
  const { hadExistingServer, registered } = registerServer(serverConfig);

  assertRegisteredConfig(registered, serverConfig);

  const listAfter = runCommand("codex", ["mcp", "list"]);
  if (!(listAfter.stdout || "").includes(SERVER_NAME)) {
    fail(`'codex mcp list' no muestra ${SERVER_NAME} tras el bootstrap.`);
  }

  const summary = {
    server: SERVER_NAME,
    source: path.relative(repoRoot, serverConfig.mcpConfigPath) || "mcp.json",
    action: hadExistingServer || hadListedServer ? "updated" : "created",
    command: registered.transport.command,
    args: registered.transport.args,
    env: {
      API_KEY: "[configured]",
    },
  };

  console.log("[testsprite-bootstrap] Registro completado.");
  console.log(JSON.stringify(summary, null, 2));
}

main();
