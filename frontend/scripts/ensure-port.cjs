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
 * Kill a process by PID - try SIGKILL directly for reliability
 */
function killProcess(pid) {
  try {
    // Use SIGKILL directly - we want these gone immediately
    process.kill(pid, "SIGKILL");
    log(`Killed PID ${pid} (SIGKILL)`);
    return true;
  } catch (e) {
    if (e.code === "EPERM") {
      // Try with sudo via shell
      try {
        execSync(`sudo kill -9 ${pid} 2>/dev/null`, { encoding: "utf8" });
        log(`Killed PID ${pid} via sudo`);
        return true;
      } catch {
        error(`Permission denied killing PID ${pid} (owned by another user)`);
        return false;
      }
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

  // Get processes using the port FIRST
  const pids = getPidsOnPort(PORT);

  if (pids.length > 0) {
    log(`Found ${pids.length} process(es) on port ${PORT}:`);
    for (const pid of pids) {
      const name = getProcessInfo(pid);
      log(`  PID ${pid}: ${name}`);
    }

    // Kill ALL of them immediately
    log(`Killing all processes on port ${PORT}...`);
    for (const pid of pids) {
      killProcess(pid);
    }

    // Also try pkill for any node processes that might be hanging
    // NOTE: Be very specific to avoid killing unrelated processes
    try {
      execSync(`pkill -9 -f "node.*vite.*--port.*${PORT}" 2>/dev/null || true`, {
        encoding: "utf8",
      });
    } catch {}

    // Wait for kills to take effect
    await sleep(500);
  }

  // Check if port is now free
  if (await isPortAvailable(PORT)) {
    success(`Port ${PORT} is available`);
    return true;
  }

  // Retry with exponential backoff (for TIME_WAIT)
  let waitMs = INITIAL_WAIT_MS;
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    // Check for any new processes that appeared
    const currentPids = getPidsOnPort(PORT);
    if (currentPids.length > 0) {
      log(`Found lingering processes: ${currentPids.join(", ")}, killing...`);
      for (const pid of currentPids) {
        killProcess(pid);
      }
    }

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
