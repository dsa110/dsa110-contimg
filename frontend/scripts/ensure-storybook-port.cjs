#!/usr/bin/env node
/**
 * Ensures Storybook port (6100) is available before starting.
 *
 * Features:
 * - Kills any existing process using the Storybook port
 * - Uses graceful SIGTERM first, then SIGKILL
 * - Retries with exponential backoff for TIME_WAIT
 * - Handles permission errors gracefully
 */

const { execSync } = require("child_process");
const net = require("net");

const PORT = 6100;
const MAX_RETRIES = 5;
const INITIAL_WAIT_MS = 500;

function log(msg) {
  console.log(`[storybook-port] ${msg}`);
}

function error(msg) {
  console.error(`[storybook-port] ERROR: ${msg}`);
}

function success(msg) {
  console.log(`[storybook-port] ✓ ${msg}`);
}

/**
 * Get PIDs using the specified port
 */
function getPidsOnPort(port) {
  try {
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
 * Get process info for a PID
 */
function getProcessInfo(pid) {
  try {
    const result = execSync(`ps -p ${pid} -o comm= 2>/dev/null`, {
      encoding: "utf8",
    });
    return result.trim();
  } catch {
    return "unknown";
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
 * Kill a process by PID - graceful first, then force
 */
function killProcess(pid, processName) {
  try {
    // Try SIGTERM first (graceful)
    process.kill(pid, "SIGTERM");
    log(`Sent SIGTERM to ${processName} (PID ${pid})`);
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
 * Main function to ensure port is available
 */
async function ensurePortAvailable() {
  log(`Checking port ${PORT}...`);

  // Check if port is already available
  if (await isPortAvailable(PORT)) {
    success(`Port ${PORT} is available`);
    return true;
  }

  // Get processes using the port
  const pids = getPidsOnPort(PORT);
  if (pids.length === 0) {
    // Port in TIME_WAIT or similar - wait and retry
    log(`Port ${PORT} unavailable but no process found (likely TIME_WAIT)`);
  } else {
    // Kill processes using the port
    for (const pid of pids) {
      const processName = getProcessInfo(pid);
      log(`Found ${processName} (PID ${pid}) on port ${PORT}`);
      killProcess(pid, processName);
    }
  }

  // Wait and retry with exponential backoff
  let waitMs = INITIAL_WAIT_MS;
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    await sleep(waitMs);

    if (await isPortAvailable(PORT)) {
      success(`Port ${PORT} is now available`);
      return true;
    }

    // Force kill any remaining processes
    const remainingPids = getPidsOnPort(PORT);
    for (const pid of remainingPids) {
      forceKillProcess(pid);
    }

    log(`Retry ${attempt}/${MAX_RETRIES}, waiting ${waitMs}ms...`);
    waitMs = Math.min(waitMs * 2, 5000);
  }

  // Final check
  if (await isPortAvailable(PORT)) {
    success(`Port ${PORT} is now available`);
    return true;
  }

  error(`Could not free port ${PORT} after ${MAX_RETRIES} retries`);
  const finalPids = getPidsOnPort(PORT);
  if (finalPids.length > 0) {
    error(`Still occupied by PIDs: ${finalPids.join(", ")}`);
    for (const pid of finalPids) {
      const info = getProcessInfo(pid);
      error(`  - ${info} (PID ${pid})`);
    }
  }
  process.exit(1);
}

// Run
ensurePortAvailable().catch((e) => {
  error(e.message);
  process.exit(1);
});
