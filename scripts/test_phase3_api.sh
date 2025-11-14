#!/bin/bash
# Test Phase 3 API endpoints using curl
# Assumes backend server is running on localhost:8000

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "============================================================"
echo "Testing Phase 3 API Endpoints"
echo "============================================================"
echo ""

# Test Event Bus Endpoints
echo "=== Event Bus Endpoints ==="
echo ""

echo "1. GET /api/events/stream"
curl -s "${BASE_URL}/api/events/stream?limit=10" | python3 -m json.tool | head -30
echo ""

echo "2. GET /api/events/stats"
curl -s "${BASE_URL}/api/events/stats" | python3 -m json.tool
echo ""

echo "3. GET /api/events/types"
curl -s "${BASE_URL}/api/events/types" | python3 -m json.tool
echo ""

# Test Cache Endpoints
echo "=== Cache Endpoints ==="
echo ""

echo "4. GET /api/cache/stats"
curl -s "${BASE_URL}/api/cache/stats" | python3 -m json.tool
echo ""

echo "5. GET /api/cache/keys"
curl -s "${BASE_URL}/api/cache/keys?limit=10" | python3 -m json.tool
echo ""

echo "6. GET /api/cache/keys with pattern"
curl -s "${BASE_URL}/api/cache/keys?pattern=variability_stats:*&limit=5" | python3 -m json.tool
echo ""

echo "7. GET /api/cache/performance"
curl -s "${BASE_URL}/api/cache/performance" | python3 -m json.tool
echo ""

echo "============================================================"
echo "API endpoint tests complete!"
echo "============================================================"

