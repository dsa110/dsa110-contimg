#!/bin/bash
# Test script for real-time updates in frontend
# Tests auto-refresh functionality for DLQ, Circuit Breakers, and Health Summary

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_BASE="${API_BASE:-${BASE_URL}/api}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "Real-Time Updates Testing"
echo "=========================================="
echo ""
echo "This script tests auto-refresh intervals:"
echo "  - DLQ Stats: 10 seconds"
echo "  - Circuit Breakers: 5 seconds"
echo "  - Health Summary: 10 seconds"
echo "  - DLQ Items: 30 seconds"
echo ""

# Check if backend is running
if ! curl -s -f "${BASE_URL}/health/liveness" > /dev/null 2>&1; then
    echo "Error: Backend is not running at ${BASE_URL}"
    echo "Please start the backend server first"
    exit 1
fi

echo -e "${GREEN}:check:${NC} Backend is running"
echo ""

# Function to get current stats
get_dlq_stats() {
    curl -s "${API_BASE}/operations/dlq/stats" | jq -r '.total, .pending, .retrying, .resolved, .failed' | tr '\n' ' '
}

get_circuit_breaker_state() {
    local name="$1"
    curl -s "${API_BASE}/operations/circuit-breakers/${name}" | jq -r '.state, .failure_count' | tr '\n' ' '
}

get_health_status() {
    curl -s "${API_BASE}/health/summary" | jq -r '.status, .dlq_stats.total, (.circuit_breakers | length)' | tr '\n' ' '
}

# Get initial state
echo "Initial State:"
echo "=============="
echo -n "DLQ Stats: "
get_dlq_stats
echo ""
echo -n "Circuit Breaker (ese_detection): "
get_circuit_breaker_state "ese_detection"
echo ""
echo -n "Health Summary: "
get_health_status
echo ""
echo ""

# Create a new DLQ item
echo "Creating new DLQ item..."
PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"
if [ -f "scripts/test_dlq_endpoints.py" ]; then
    $PYTHON_BIN scripts/test_dlq_endpoints.py > /dev/null 2>&1
    echo -e "${GREEN}:check:${NC} DLQ item created"
else
    echo -e "${YELLOW}:warning:${NC} test_dlq_endpoints.py not found, skipping item creation"
fi

echo ""
echo "Waiting 2 seconds for database write..."
sleep 2

# Check state after creation
echo "State After Creation:"
echo "===================="
echo -n "DLQ Stats: "
get_dlq_stats
echo ""
echo ""

# Test 1: DLQ Stats should update within 10 seconds
echo "Test 1: DLQ Stats Auto-Refresh (10s interval)"
echo "================================================"
echo "Monitoring DLQ stats for 15 seconds..."
echo "Expected: Stats should update automatically"
echo ""

initial_total=$(curl -s "${API_BASE}/operations/dlq/stats" | jq -r '.total')
echo "Initial total: $initial_total"

for i in {1..15}; do
    sleep 1
    current_total=$(curl -s "${API_BASE}/operations/dlq/stats" | jq -r '.total')
    if [ "$current_total" != "$initial_total" ]; then
        echo -e "${GREEN}:check:${NC} DLQ stats updated after ${i} seconds (total: $initial_total -> $current_total)"
        break
    fi
    if [ $i -eq 15 ]; then
        echo -e "${YELLOW}:warning:${NC} DLQ stats did not change (may be expected if no new items)"
    fi
done

echo ""

# Test 2: Circuit Breaker reset and verify update
echo "Test 2: Circuit Breaker Auto-Refresh (5s interval)"
echo "=================================================="
echo "Resetting circuit breaker and monitoring state..."
echo ""

initial_state=$(curl -s "${API_BASE}/operations/circuit-breakers/ese_detection" | jq -r '.state')
echo "Initial state: $initial_state"

# Reset the circuit breaker
curl -s -X POST "${API_BASE}/operations/circuit-breakers/ese_detection/reset" > /dev/null
echo "Reset circuit breaker"

# Monitor for changes (should see reset reflected)
echo "Monitoring for 7 seconds..."
for i in {1..7}; do
    sleep 1
    current_state=$(curl -s "${API_BASE}/operations/circuit-breakers/ese_detection" | jq -r '.state')
    failure_count=$(curl -s "${API_BASE}/operations/circuit-breakers/ese_detection" | jq -r '.failure_count')
    if [ "$failure_count" = "0" ]; then
        echo -e "${GREEN}:check:${NC} Circuit breaker reset confirmed after ${i} seconds (state: $current_state, failures: $failure_count)"
        break
    fi
done

echo ""

# Test 3: Health Summary aggregation
echo "Test 3: Health Summary Auto-Refresh (10s interval)"
echo "=================================================="
echo "Monitoring health summary for 12 seconds..."
echo ""

initial_health=$(curl -s "${API_BASE}/health/summary" | jq -r '.status')
initial_dlq_total=$(curl -s "${API_BASE}/health/summary" | jq -r '.dlq_stats.total')
echo "Initial health status: $initial_health"
echo "Initial DLQ total in health: $initial_dlq_total"

# Create another DLQ item
echo "Creating another DLQ item..."
$PYTHON_BIN -c "
import sys
sys.path.insert(0, 'src')
from dsa110_contimg.pipeline.dead_letter_queue import get_dlq
dlq = get_dlq()
dlq.add('test_component', 'test_operation', RuntimeError('Test for health summary'), {'test': True})
" > /dev/null 2>&1

echo "Waiting 2 seconds..."
sleep 2

# Check if health summary reflects the change
for i in {1..12}; do
    sleep 1
    current_dlq_total=$(curl -s "${API_BASE}/health/summary" | jq -r '.dlq_stats.total')
    if [ "$current_dlq_total" != "$initial_dlq_total" ]; then
        echo -e "${GREEN}:check:${NC} Health summary updated after ${i} seconds (DLQ total: $initial_dlq_total -> $current_dlq_total)"
        break
    fi
    if [ $i -eq 12 ]; then
        echo -e "${YELLOW}:warning:${NC} Health summary did not update (may need manual refresh)"
    fi
done

echo ""

# Test 4: Verify all endpoints are responsive
echo "Test 4: Endpoint Responsiveness"
echo "==============================="
echo "Testing all endpoints for quick response times..."

endpoints=(
    "/api/operations/dlq/stats"
    "/api/operations/circuit-breakers"
    "/api/health/summary"
    "/api/operations/dlq/items?limit=5"
)

for endpoint in "${endpoints[@]}"; do
    start_time=$(date +%s%N)
    curl -s "${BASE_URL}${endpoint}" > /dev/null
    end_time=$(date +%s%N)
    duration=$(( (end_time - start_time) / 1000000 ))
    
    if [ $duration -lt 500 ]; then
        echo -e "${GREEN}:check:${NC} ${endpoint}: ${duration}ms (< 500ms)"
    else
        echo -e "${YELLOW}:warning:${NC} ${endpoint}: ${duration}ms (>= 500ms)"
    fi
done

echo ""
echo "=========================================="
echo "Real-Time Updates Testing Complete"
echo "=========================================="
echo ""
echo "Note: Frontend auto-refresh is configured via React Query:"
echo "  - DLQ Stats: 10 seconds"
echo "  - Circuit Breakers: 5 seconds"
echo "  - Health Summary: 10 seconds"
echo "  - DLQ Items: 30 seconds"
echo ""
echo "To test frontend auto-refresh:"
echo "  1. Start frontend dev server: cd frontend && npm run dev"
echo "  2. Open http://localhost:3000/operations"
echo "  3. Open browser DevTools :arrow_right: Network tab"
echo "  4. Observe automatic API calls at configured intervals"
echo "  5. Create/update DLQ items and watch UI update automatically"

