#!/bin/bash
# Quick start script for Absurd pipeline control
# This script sets up and starts the Absurd system for pipeline control

set -e

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║          DSA-110 Absurd Pipeline Control - Quick Start                ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Check prerequisites
echo ":clipboard: Step 1: Checking prerequisites..."
echo ""

if ! command -v psql &> /dev/null; then
    echo ":cross: PostgreSQL client (psql) not found"
    echo "   Install with: sudo apt install postgresql-client"
    exit 1
fi

if ! command -v python &> /dev/null; then
    echo ":cross: Python not found"
    exit 1
fi

echo ":check: Prerequisites OK"
echo ""

# Step 2: Database setup
echo ":clipboard: Step 2: Setting up Absurd database..."
echo ""

if [ -f "scripts/absurd/setup_absurd_db.sh" ]; then
    bash scripts/absurd/setup_absurd_db.sh
else
    echo ":warning:  Database setup script not found (this is OK if database already exists)"
fi
echo ""

# Step 3: Create queue
echo ":clipboard: Step 3: Creating Absurd queue..."
echo ""

if [ -f "scripts/absurd/create_absurd_queues.sh" ]; then
    bash scripts/absurd/create_absurd_queues.sh
else
    echo ":warning:  Queue creation script not found (this is OK if queue already exists)"
fi
echo ""

# Step 4: Set environment variables
echo ":clipboard: Step 4: Setting environment variables..."
echo ""

export ABSURD_ENABLED=true
export ABSURD_DATABASE_URL=${ABSURD_DATABASE_URL:-"postgresql://postgres:postgres@localhost/dsa110_absurd"}
export ABSURD_QUEUE_NAME=${ABSURD_QUEUE_NAME:-"dsa110-pipeline"}
export ABSURD_WORKER_CONCURRENCY=${ABSURD_WORKER_CONCURRENCY:-4}

echo "   ABSURD_ENABLED=$ABSURD_ENABLED"
echo "   ABSURD_DATABASE_URL=$ABSURD_DATABASE_URL"
echo "   ABSURD_QUEUE_NAME=$ABSURD_QUEUE_NAME"
echo "   ABSURD_WORKER_CONCURRENCY=$ABSURD_WORKER_CONCURRENCY"
echo ""

# Step 5: Test connection
echo ":clipboard: Step 5: Testing database connection..."
echo ""

if [ -f "scripts/absurd/test_absurd_connection.py" ]; then
    python scripts/absurd/test_absurd_connection.py
    if [ $? -eq 0 ]; then
        echo ":check: Database connection OK"
    else
        echo ":cross: Database connection failed"
        exit 1
    fi
else
    echo ":warning:  Test script not found, skipping connection test"
fi
echo ""

# Step 6: Instructions
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                    :check: Setup Complete!                                  ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1:variation_selector-16:⃣  Start the API server (Terminal 1):"
echo "   uvicorn src.dsa110_contimg.api.routes:app --host 0.0.0.0 --port 8000"
echo ""
echo "2:variation_selector-16:⃣  Start the Absurd worker (Terminal 2):"
echo "   python scripts/absurd/start_worker.py"
echo ""
echo "3:variation_selector-16:⃣  Submit a test task:"
echo "   python scripts/absurd/submit_test_task.py"
echo ""
echo "For more information:"
echo "   docs/how-to/operating_absurd_pipeline.md"
echo ""

