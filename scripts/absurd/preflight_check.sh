#!/bin/bash
# Pre-flight checklist for ABSURD deployment
# Run this before starting the deployment

set -e
echo "=== ABSURD Deployment Pre-Flight Checklist ==="
echo ""

# 1. Verify conda environment
echo "1. Checking conda environment..."
if conda info --envs | grep -q "casa6"; then
    echo "   ✅ casa6 environment exists"
else
    echo "   ❌ casa6 environment NOT FOUND"
    exit 1
fi

# 2. Verify absurd module exists
echo "2. Checking ABSURD module..."
ABSURD_DIR="/data/dsa110-contimg/backend/src/dsa110_contimg/absurd"
REQUIRED_FILES="config.py client.py worker.py schema.sql adapter.py"
for f in $REQUIRED_FILES; do
    if [[ -f "$ABSURD_DIR/$f" ]]; then
        echo "   ✅ $f exists"
    else
        echo "   ❌ $f MISSING"
        exit 1
    fi
done

# 3. Verify PostgreSQL is running
echo "3. Checking PostgreSQL..."
if pg_isready -h /var/run/postgresql -p 5433 -q 2>/dev/null; then
    echo "   ✅ PostgreSQL is running on port 5433"
else
    echo "   ❌ PostgreSQL is NOT running"
    exit 1
fi

# 4. Verify database exists
echo "4. Checking ABSURD database..."
if psql -h /var/run/postgresql -p 5433 -d dsa110_absurd -c "SELECT 1" >/dev/null 2>&1; then
    echo "   ✅ dsa110_absurd database exists"
else
    echo "   ❌ dsa110_absurd database MISSING"
    exit 1
fi

# 5. Verify asyncpg is installed
echo "5. Checking Python dependencies..."
if python -c "import asyncpg" 2>/dev/null; then
    echo "   ✅ asyncpg is installed"
else
    echo "   ⚠️  asyncpg NOT installed"
fi

# 6. Check disk space
echo "6. Checking disk space..."
AVAILABLE=$(df -BG /data | tail -1 | awk '{print $4}' | tr -d 'G')
if [[ $AVAILABLE -gt 10 ]]; then
    echo "   ✅ ${AVAILABLE}GB available on /data"
else
    echo "   ⚠️  Only ${AVAILABLE}GB available (recommend >10GB)"
fi

echo ""
echo "=== Pre-Flight Check Complete ==="
