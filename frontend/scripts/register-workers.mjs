#!/usr/bin/env node
/**
 * Register ABSURD workers with the API by sending heartbeats.
 *
 * This script finds running ABSURD worker processes and registers them
 * with the API by sending heartbeat requests.
 */
import { execSync } from "child_process";

const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:8000";

async function main() {
  console.log("🔍 Finding ABSURD worker processes...");

  // Find worker process IDs
  let psOutput;
  try {
    psOutput = execSync(
      'ps aux | grep "dsa110_contimg.absurd" | grep -v grep',
      { encoding: "utf-8" }
    );
  } catch {
    console.log("❌ No ABSURD worker processes found");
    return;
  }

  const lines = psOutput.trim().split("\n").filter(Boolean);
  console.log(`Found ${lines.length} worker process(es)`);

  // Get auth token
  console.log("🔑 Getting auth token...");
  const loginRes = await fetch(`${BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "admin", password: "admin" }),
  });

  if (!loginRes.ok) {
    console.error("❌ Failed to login");
    return;
  }

  const { tokens } = await loginRes.json();
  const authHeader = `Bearer ${tokens.access_token}`;

  // Register each worker with a heartbeat
  for (let i = 0; i < lines.length; i++) {
    const workerId = `manual-worker-${i + 1}`;
    console.log(`💓 Sending heartbeat for ${workerId}...`);

    const hbRes = await fetch(
      `${BASE_URL}/absurd/workers/${workerId}/heartbeat`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: authHeader,
        },
        body: JSON.stringify({}),
      }
    );

    if (hbRes.ok) {
      console.log(`   ✅ Registered ${workerId}`);
    } else {
      console.log(`   ❌ Failed: ${hbRes.status}`);
    }
  }

  // Check workers list
  console.log("\n📊 Checking registered workers...");
  const workersRes = await fetch(`${BASE_URL}/absurd/workers`, {
    headers: { Authorization: authHeader },
  });

  if (workersRes.ok) {
    const data = await workersRes.json();
    console.log(`Total workers: ${data.total}`);
    console.log(`Active: ${data.active}, Idle: ${data.idle}`);
    if (data.workers) {
      data.workers.forEach((w) => {
        console.log(`  - ${w.worker_id}: ${w.state}`);
      });
    }
  }

  // Check health
  console.log("\n🏥 Checking ABSURD health...");
  const healthRes = await fetch(`${BASE_URL}/absurd/health/detailed`, {
    headers: { Authorization: authHeader },
  });

  if (healthRes.ok) {
    const health = await healthRes.json();
    console.log(`Status: ${health.status}`);
    console.log(`Message: ${health.message}`);
    console.log(`Worker pool healthy: ${health.worker_pool_healthy}`);
  }
}

main().catch(console.error);
