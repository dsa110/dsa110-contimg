#!/usr/bin/env node
/**
 * Ensures port 3000 is available for the dev server.
 *
 * Features:
 * - Kills any process using port 3000
 * - Retries with exponential backoff for TIME_WAIT
 * - Handles permission errors gracefully
 * - Cross-platform support (Linux/macOS)
 */

const { execSync } = require("child_process");
const net = require("net");

const PORT = 3000;
const MAX_RETRIES = 5;
const INITIAL_WAIT_MS = 500;

function log(msg) {
  console.log(`[ensure-port] ${msg}`);
}

function error(msg) {
  console.error(`[ensure-port] ERROR ${msg}`);
}

function success(msg) {
  console.log(`[ensure-port] OK ${msg}`);
}

/**
 * Get PIDs using the specified port
 */
function getPidsOnPort(port) {
  try {
    // Try lsof first (Linux/macOS)
    const result = execSync(`lsof -ti:${port} 2>/dev/null`, {
      encoding: "utf8",
    });
    return result.trim().split("\n").filter(Boolean).map(Number);
  } catch (e) {
    // lsof returns non-zero if no processes found
    return [];
  }
}

/**
 * Check if port is available by trying to bind to it
 */
function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close();
      resolve(true);
    });
    server.listen(port, "127.0.0.1");
  });
}

/**
 * Kill a process by PID with SIGTERM
 */
function killProcess(pid) {
  try {
    process.kill(pid, "SIGTERM");
    log(`Sent SIGTERM to PID ${pid}`);
    return true;
  } catch (e) {
    if (e.code === "EPERM") {
      error(`Permission denied killing PID ${pid} (owned by another user)`);
      return false;
    } else if (e.code === "ESRCH") {
      // Process already dead
      return true;
    }
    error(`Failed to kill PID ${pid}: ${e.message}`);
    return false;
  }
}

/**
 * Force kill a process by PID with SIGKILL
 */
function forceKillProcess(pid) {
  try {
    process.kill(pid, "SIGKILL");
    log(`Sent SIGKILL to PID ${pid}`);
    return true;
  } catch (e) {
    if (e.code === "ESRCH") return true; // Already dead
    return false;
  }
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Get process info for a PID
 */
function getProcessInfo(pid) {
  try {
    const result = execSync(`ps -p ${pid} -o comm= 2>/dev/null`, {
      encoding: "utf8",
    });
    return result.trim();
  } catch (e) {
    return "unknown";
  }
}

/**
 * Main function to ensure port is available
 */
async function ensurePortAvailable() {
  log(`Ensuring port ${PORT} is available...`);

  // Check if port is already free
  if (await isPortAvailable(PORT)) {
    success(`Port ${PORT} is available`);
    return true;
  }

  // Get processes using the port
  const pids = getPidsOnPort(PORT);

  if (pids.length === 0) {
    // Port busy but no PIDs found - might be TIME_WAIT
    log(`Port ${PORT} busy but no processes found (possibly TIME_WAIT state)`);
  } else {
    log(`Found ${pids.length} process(es) on port ${PORT}:`);
    for (const pid of pids) {
      const name = getProcessInfo(pid);
      log(`  PID ${pid}: ${name}`);
    }

    // Try graceful termination first
    let permissionDenied = false;
    for (const pid of pids) {
      if (!killProcess(pid)) {
        permissionDenied = true;
      }
    }

    if (permissionDenied) {
      error(`Some processes couldn't be killed due to permissions.`);
      error(`Try running: sudo kill -9 ${pids.join(" ")}`);
      process.exit(1);
    }

    // Wait a moment for graceful shutdown
    await sleep(1000);

    // Force kill any remaining
    const remainingPids = getPidsOnPort(PORT);
    for (const pid of remainingPids) {
      log(`Process ${pid} didn't exit gracefully, force killing...`);
      forceKillProcess(pid);
    }
  }

  // Retry with exponential backoff (for TIME_WAIT)
  let waitMs = INITIAL_WAIT_MS;
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    await sleep(waitMs);

    if (await isPortAvailable(PORT)) {
      success(`Port ${PORT} is now available (attempt ${attempt})`);
      return true;
    }

    log(`Port ${PORT} still busy, waiting ${waitMs}ms... (attempt ${attempt}/${MAX_RETRIES})`);
    waitMs *= 2; // Exponential backoff
  }

  // Final check
  const finalPids = getPidsOnPort(PORT);
  if (finalPids.length > 0) {
    error(`Cannot free port ${PORT}. Processes still running: ${finalPids.join(", ")}`);
    error(`Try: sudo kill -9 ${finalPids.join(" ")}`);
  } else {
    error(`Port ${PORT} unavailable (likely TIME_WAIT or system reservation)`);
    error(`Options:`);
    error(`  1. Wait 30-60 seconds for TIME_WAIT to expire`);
    error(`  2. Run: sudo sysctl -w net.ipv4.tcp_tw_reuse=1`);
  }

  process.exit(1);
}

// Run
ensurePortAvailable().catch((e) => {
  error(`Unexpected error: ${e.message}`);
  process.exit(1);
});
