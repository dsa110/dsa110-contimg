#!/usr/bin/env node
/**
 * Ensures port 3000 is available for the dev server.
 *
 * Features:
 * - Checks backend API is running before starting frontend
 * - Gracefully stops any process using port 3000
 * - Retries with exponential backoff for TIME_WAIT
 * - Handles permission errors gracefully
 * - Cross-platform support (Linux/macOS)
 *
 * ## Graceful Shutdown (SIGTERM before SIGKILL)
 *
 * This script uses SIGTERM first and waits for graceful shutdown before
 * falling back to SIGKILL. This is important for Vite's esbuild service.
 *
 * ### Background
 *
 * Vite spawns esbuild as a long-lived child process that handles TypeScript/JSX
 * compilation. The parent (Vite) and child (esbuild) communicate via IPC.
 *
 * When Vite is terminated with SIGKILL:
 * - The process dies immediately without cleanup
 * - esbuild's IPC channels may be left in an inconsistent state
 * - Subsequent Vite instances may inherit or encounter these broken channels
 *
 * This likely causes the error:
 *   "The service is no longer running"
 *   at esbuild/lib/main.js
 *
 * The error indicates esbuild's internal service (a child process) is no longer
 * responding to IPC requests, probably because it was terminated abruptly or
 * its communication channel was corrupted.
 *
 * ### Solution
 *
 * Use SIGTERM first, which allows:
 * 1. Vite to catch the signal and clean up
 * 2. esbuild child process to terminate gracefully
 * 3. IPC channels to close properly
 *
 * Only use SIGKILL as a last resort after 3 seconds.
 *
 * ### References
 * - esbuild service lifecycle: node_modules/vite/node_modules/esbuild/lib/main.js
 * - Error originates from closeData.didClose flag set when child process exits
 */

const { execSync } = require("child_process");
const net = require("net");
const http = require("http");

const PORT = 3000;
const MAX_RETRIES = 5;
const INITIAL_WAIT_MS = 500;
const BACKEND_URL = "http://localhost:8000";
const BACKEND_HEALTH_ENDPOINT = "/api/health";

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
 * Check if a process is still running
 */
function isProcessRunning(pid) {
  try {
    process.kill(pid, 0); // Signal 0 = just check if process exists
    return true;
  } catch (e) {
    return false;
  }
}

/**
 * Kill a process by PID - use graceful shutdown first, then force kill
 *
 * This is critical for esbuild: SIGKILL causes "The service is no longer running"
 * errors because esbuild's child process gets terminated mid-operation without
 * cleanup. SIGTERM allows graceful shutdown.
 */
async function killProcess(pid) {
  // First try SIGTERM (graceful shutdown)
  try {
    process.kill(pid, "SIGTERM");
    log(`Sent SIGTERM to PID ${pid}`);
  } catch (e) {
    if (e.code === "ESRCH") {
      // Process already dead
      return true;
    }
    if (e.code === "EPERM") {
      // Try with sudo
      try {
        execSync(`sudo kill -15 ${pid} 2>/dev/null`, { encoding: "utf8" });
        log(`Sent SIGTERM to PID ${pid} via sudo`);
      } catch {
        error(`Permission denied killing PID ${pid} (owned by another user)`);
        return false;
      }
    } else {
      error(`Failed to signal PID ${pid}: ${e.message}`);
      return false;
    }
  }

  // Wait up to 3 seconds for graceful shutdown
  for (let i = 0; i < 6; i++) {
    await sleep(500);
    if (!isProcessRunning(pid)) {
      log(`PID ${pid} terminated gracefully`);
      return true;
    }
  }

  // Process still running - now use SIGKILL
  log(`PID ${pid} did not terminate gracefully, sending SIGKILL`);
  try {
    process.kill(pid, "SIGKILL");
    log(`Sent SIGKILL to PID ${pid}`);
    return true;
  } catch (e) {
    if (e.code === "ESRCH") return true; // Already dead
    if (e.code === "EPERM") {
      try {
        execSync(`sudo kill -9 ${pid} 2>/dev/null`, { encoding: "utf8" });
        log(`Killed PID ${pid} via sudo`);
        return true;
      } catch {
        return false;
      }
    }
    return false;
  }
}

/**
 * Force kill a process by PID with SIGKILL (use sparingly)
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
 * Check if a process is safe to kill (only vite/node dev server processes)
 */
function isSafeToKill(pid) {
  try {
    const cmdline = execSync(`ps -p ${pid} -o args= 2>/dev/null`, {
      encoding: "utf8",
    }).trim();
    // Only kill node/vite processes, not sshd, bash, or other system processes
    const safePatterns = [/vite/i, /node.*dev/i, /npm.*dev/i, /esbuild/i];
    const dangerousPatterns = [/sshd/i, /bash/i, /zsh/i, /systemd/i, /init/i];

    // Check if it matches dangerous patterns first
    for (const pattern of dangerousPatterns) {
      if (pattern.test(cmdline)) {
        log(
          `Skipping PID ${pid} (${cmdline.slice(0, 50)}...) - system process`
        );
        return false;
      }
    }

    // Check if it matches safe patterns
    for (const pattern of safePatterns) {
      if (pattern.test(cmdline)) {
        return true;
      }
    }

    // If we can't determine, skip it to be safe
    log(
      `Skipping PID ${pid} (${cmdline.slice(
        0,
        50
      )}...) - not a recognized dev server`
    );
    return false;
  } catch (e) {
    return false;
  }
}

/**
 * Check if the backend API is running and healthy
 */
function checkBackendHealth() {
  return new Promise((resolve) => {
    const url = new URL(BACKEND_HEALTH_ENDPOINT, BACKEND_URL);
    const req = http.get(url.href, { timeout: 5000 }, (res) => {
      resolve(res.statusCode >= 200 && res.statusCode < 400);
    });
    req.on("error", () => resolve(false));
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
  });
}

/**
 * Main function to ensure port is available
 */
async function ensurePortAvailable() {
  // First, check that the backend API is running
  log(`Checking backend API at ${BACKEND_URL}...`);
  const backendHealthy = await checkBackendHealth();
  if (!backendHealthy) {
    error(`Backend API not running at ${BACKEND_URL}`);
    error(``);
    error(`The frontend requires the backend API to be running.`);
    error(`Start the backend first:`);
    error(``);
    error(`  sudo systemctl start contimg-api`);
    error(``);
    error(`Or run manually:`);
    error(`  cd /data/dsa110-contimg/backend/src`);
    error(`  conda activate casa6`);
    error(`  uvicorn dsa110_contimg.api.app:app --host 0.0.0.0 --port 8000`);
    error(``);
    process.exit(1);
  }
  success(`Backend API is healthy`);

  log(`Ensuring port ${PORT} is available...`);

  // Get processes using the port FIRST
  const pids = getPidsOnPort(PORT);

  if (pids.length > 0) {
    log(`Found ${pids.length} process(es) on port ${PORT}:`);
    for (const pid of pids) {
      const name = getProcessInfo(pid);
      log(`  PID ${pid}: ${name}`);
    }

    // Kill only SAFE processes (dev servers, not system processes)
    log(`Stopping dev server processes on port ${PORT}...`);
    for (const pid of pids) {
      if (isSafeToKill(pid)) {
        await killProcess(pid);
      }
    }

    // Also try pkill for any node processes that might be hanging
    // NOTE: Be very specific to avoid killing unrelated processes
    // Use SIGTERM first for graceful shutdown
    try {
      execSync(
        `pkill -15 -f "node.*vite.*--port.*${PORT}" 2>/dev/null || true`,
        {
          encoding: "utf8",
        }
      );
      // Give processes time to shut down gracefully
      await sleep(1000);
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
      log(`Found lingering processes: ${currentPids.join(", ")}, checking...`);
      for (const pid of currentPids) {
        if (isSafeToKill(pid)) {
          await killProcess(pid);
        }
      }
    }

    await sleep(waitMs);

    if (await isPortAvailable(PORT)) {
      success(`Port ${PORT} is now available (attempt ${attempt})`);
      return true;
    }

    log(
      `Port ${PORT} still busy, waiting ${waitMs}ms... (attempt ${attempt}/${MAX_RETRIES})`
    );
    waitMs *= 2; // Exponential backoff
  }

  // Final check
  const finalPids = getPidsOnPort(PORT);
  if (finalPids.length > 0) {
    error(
      `Cannot free port ${PORT}. Processes still running: ${finalPids.join(
        ", "
      )}`
    );
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
