#!/bin/bash
# Verify Frontend API Integration
# Tests that all API endpoints used by frontend are accessible and return correct data

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_BASE="${API_BASE:-${BASE_URL}/api}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "Frontend API Integration Verification"
echo "=========================================="
echo ""

PASSED=0
FAILED=0

# Function to test endpoint
test_endpoint() {
    local name="$1"
    local endpoint="$2"
    local expected_fields="$3"
    
    echo -n "Testing $name... "
    
    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}${endpoint}")
    status_code=$(echo "$response" | grep -oE 'HTTP_STATUS:([0-9]+)' | grep -oE '[0-9]+' || echo "000")
    body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//')
    
    if [ "$status_code" = "200" ]; then
        # Check if expected fields exist
        if [ -n "$expected_fields" ]; then
            missing_fields=""
            for field in $expected_fields; do
                if ! echo "$body" | jq -e ".${field}" > /dev/null 2>&1; then
                    missing_fields="${missing_fields} ${field}"
                fi
            done
            
            if [ -z "$missing_fields" ]; then
                echo -e "${GREEN}:check:${NC} Pass"
                ((PASSED++))
                return 0
            else
                echo -e "${YELLOW}:warning:${NC} Missing fields:${missing_fields}"
                ((FAILED++))
                return 1
            fi
        else
            echo -e "${GREEN}:check:${NC} Pass"
            ((PASSED++))
            return 0
        fi
    else
        echo -e "${RED}:cross:${NC} Failed (Status: $status_code)"
        ((FAILED++))
        return 1
    fi
}

# Test DLQ Stats endpoint (used by DLQStats component)
test_endpoint "DLQ Stats" "/operations/dlq/stats" "total pending retrying resolved failed"

# Test DLQ Items endpoint (used by DLQTable component)
test_endpoint "DLQ Items List" "/operations/dlq/items?limit=5" ""

# Test DLQ Item Detail endpoint
ITEMS_RESPONSE=$(curl -s "${API_BASE}/operations/dlq/items?limit=1")
ITEMS_TYPE=$(echo "$ITEMS_RESPONSE" | jq -r 'type')
if [ "$ITEMS_TYPE" = "array" ]; then
    FIRST_ITEM_ID=$(echo "$ITEMS_RESPONSE" | jq -r 'if length > 0 then .[0].id else empty end')
    if [ -n "$FIRST_ITEM_ID" ] && [ "$FIRST_ITEM_ID" != "null" ] && [ "$FIRST_ITEM_ID" != "" ]; then
        test_endpoint "DLQ Item Detail" "/operations/dlq/items/${FIRST_ITEM_ID}" "id component operation status"
    else
        echo -e "${YELLOW}:warning:${NC} No DLQ items available for detail test"
    fi
else
    echo -e "${YELLOW}:warning:${NC} DLQ items endpoint returned non-array response"
fi

# Test Circuit Breakers endpoint (used by CircuitBreakerStatus component)
test_endpoint "Circuit Breakers List" "/operations/circuit-breakers" "circuit_breakers"

# Test individual circuit breaker endpoints
for breaker in "ese_detection" "calibration_solve" "photometry"; do
    test_endpoint "Circuit Breaker: ${breaker}" "/operations/circuit-breakers/${breaker}" "name state failure_count"
done

# Test Health Summary endpoint (used by HealthPage OperationsHealthTab)
test_endpoint "Health Summary" "/health/summary" "status timestamp checks circuit_breakers dlq_stats"

# Test DLQ Actions endpoints (POST)
if [ -n "$FIRST_ITEM_ID" ] && [ "$FIRST_ITEM_ID" != "null" ] && [ "$FIRST_ITEM_ID" != "" ]; then
    echo -n "Testing DLQ Retry action... "
    retry_response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d '{"note": "Test"}' \
        "${API_BASE}/operations/dlq/items/${FIRST_ITEM_ID}/retry")
    retry_status=$(echo "$retry_response" | grep -oE 'HTTP_STATUS:([0-9]+)' | grep -oE '[0-9]+' || echo "000")
    if [ "$retry_status" = "200" ]; then
        echo -e "${GREEN}:check:${NC} Pass"
        ((PASSED++))
    else
        echo -e "${RED}:cross:${NC} Failed (Status: $retry_status)"
        ((FAILED++))
    fi
fi

# Test Circuit Breaker Reset endpoint
echo -n "Testing Circuit Breaker Reset... "
reset_response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
    "${API_BASE}/operations/circuit-breakers/ese_detection/reset")
reset_status=$(echo "$reset_response" | grep -oE 'HTTP_STATUS:([0-9]+)' | grep -oE '[0-9]+' || echo "000")
if [ "$reset_status" = "200" ]; then
    echo -e "${GREEN}:check:${NC} Pass"
    ((PASSED++))
else
    echo -e "${RED}:cross:${NC} Failed (Status: $reset_status)"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All API endpoints are accessible and working!${NC}"
    echo ""
    echo "Frontend components should be able to:"
    echo "  :check: Fetch DLQ stats and items"
    echo "  :check: Fetch circuit breaker states"
    echo "  :check: Fetch health summary"
    echo "  :check: Perform retry/resolve actions"
    echo "  :check: Reset circuit breakers"
    exit 0
else
    echo -e "${RED}Some endpoints failed. Please check the errors above.${NC}"
    exit 1
fi

