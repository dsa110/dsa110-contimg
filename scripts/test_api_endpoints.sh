#!/bin/bash
# Test script for Operations API endpoints
# Tests all DLQ and Circuit Breaker endpoints

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_BASE="${API_BASE:-${BASE_URL}/api}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test header
print_test() {
    echo ""
    echo "=========================================="
    echo "Testing: $1"
    echo "=========================================="
}

# Function to check response
check_response() {
    local test_name="$1"
    local response="$2"
    local expected_status="${3:-200}"
    
    # Extract HTTP status code (handle both HTTP_STATUS:XXX and HTTP/X.X XXX formats)
    local status_code=$(echo "$response" | grep -oE 'HTTP_STATUS:([0-9]+)' | grep -oE '[0-9]+' || \
                        echo "$response" | grep -oE 'HTTP/[0-9]\.[0-9] ([0-9]+)' | grep -oE '[0-9]+' || \
                        echo "000")
    local body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//' | sed 's/HTTP\/[0-9]\.[0-9] [0-9]*$//')
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} $test_name: Status $status_code"
        echo "Response body:"
        echo "$body" | jq . 2>/dev/null || echo "$body"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $test_name: Expected $expected_status, got $status_code"
        echo "Response:"
        echo "$response"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to make API call
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"
    local expected_status="${4:-200}"
    
    local url="${API_BASE}${endpoint}"
    local curl_cmd="curl -s -w '\nHTTP_STATUS:%{http_code}' -X ${method}"
    
    if [ -n "$data" ]; then
        curl_cmd="${curl_cmd} -H 'Content-Type: application/json' -d '${data}'"
    fi
    
    curl_cmd="${curl_cmd} '${url}'"
    
    local response=$(eval $curl_cmd)
    local status_code=$(echo "$response" | grep -oP 'HTTP_STATUS:\K\d+' || echo "000")
    local body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//')
    
    echo "$body"
    return $([ "$status_code" = "$expected_status" ] && echo 0 || echo 1)
}

echo "=========================================="
echo "Operations API Endpoint Testing"
echo "=========================================="
echo "Base URL: ${BASE_URL}"
echo "API Base: ${API_BASE}"
echo ""

# Check if backend is running
print_test "Backend Health Check"
if curl -s -f "${BASE_URL}/health/liveness" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend is running"
else
    echo -e "${RED}✗${NC} Backend is not running at ${BASE_URL}"
    echo "Please start the backend server first"
    exit 1
fi

# ============================================================================
# Health Summary Endpoint
# ============================================================================
print_test "Health Summary Endpoint"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/health/summary")
check_response "GET /api/health/summary" "$response" "200"

# ============================================================================
# Dead Letter Queue Endpoints
# ============================================================================

# DLQ Stats
print_test "DLQ Stats Endpoint"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/dlq/stats")
check_response "GET /api/operations/dlq/stats" "$response" "200"

# Extract initial stats for later comparison
initial_stats=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//' | jq -r '.total // 0')

# DLQ Items List (all)
print_test "DLQ Items List (All)"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/dlq/items")
check_response "GET /api/operations/dlq/items" "$response" "200"

# Extract first item ID if available
first_item_id=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//' | jq -r '.[0].id // empty')

# DLQ Items List (filtered by component)
print_test "DLQ Items List (Filtered by component: ese_detection)"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/dlq/items?component=ese_detection")
check_response "GET /api/operations/dlq/items?component=ese_detection" "$response" "200"

# DLQ Items List (filtered by status)
print_test "DLQ Items List (Filtered by status: pending)"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/dlq/items?status=pending")
check_response "GET /api/operations/dlq/items?status=pending" "$response" "200"

# DLQ Items List (pagination)
print_test "DLQ Items List (Pagination: limit=5, offset=0)"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/dlq/items?limit=5&offset=0")
check_response "GET /api/operations/dlq/items?limit=5&offset=0" "$response" "200"

# DLQ Item Detail (if items exist)
if [ -n "$first_item_id" ] && [ "$first_item_id" != "null" ]; then
    print_test "DLQ Item Detail"
    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/dlq/items/${first_item_id}")
    check_response "GET /api/operations/dlq/items/${first_item_id}" "$response" "200"
    
    # Test retry action
    print_test "DLQ Item Retry"
    retry_data='{"note": "Manual retry test"}'
    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "${retry_data}" \
        "${API_BASE}/operations/dlq/items/${first_item_id}/retry")
    check_response "POST /api/operations/dlq/items/${first_item_id}/retry" "$response" "200"
    
    # Test resolve action
    print_test "DLQ Item Resolve"
    resolve_data='{"note": "Manually resolved for testing"}'
    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "${resolve_data}" \
        "${API_BASE}/operations/dlq/items/${first_item_id}/resolve")
    check_response "POST /api/operations/dlq/items/${first_item_id}/resolve" "$response" "200"
else
    echo -e "${YELLOW}⚠${NC} No DLQ items found, skipping item detail and action tests"
    echo "   Run scripts/test_dlq_endpoints.py to create test items"
fi

# ============================================================================
# Circuit Breaker Endpoints
# ============================================================================

# Circuit Breakers List
print_test "Circuit Breakers List"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/circuit-breakers")
check_response "GET /api/operations/circuit-breakers" "$response" "200"

# Individual Circuit Breaker States
for breaker_name in "ese_detection" "calibration_solve" "photometry"; do
    print_test "Circuit Breaker State: ${breaker_name}"
    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/circuit-breakers/${breaker_name}")
    check_response "GET /api/operations/circuit-breakers/${breaker_name}" "$response" "200"
done

# Circuit Breaker Reset
print_test "Circuit Breaker Reset: ese_detection"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
    "${API_BASE}/operations/circuit-breakers/ese_detection/reset")
check_response "POST /api/operations/circuit-breakers/ese_detection/reset" "$response" "200"

# ============================================================================
# Error Handling Tests
# ============================================================================

# Invalid DLQ Item ID
print_test "Error Handling: Invalid DLQ Item ID"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/dlq/items/99999")
check_response "GET /api/operations/dlq/items/99999 (should 404)" "$response" "404"

# Invalid Circuit Breaker Name
print_test "Error Handling: Invalid Circuit Breaker Name"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/circuit-breakers/invalid_name")
check_response "GET /api/operations/circuit-breakers/invalid_name (should 404)" "$response" "404"

# Invalid Endpoint
print_test "Error Handling: Invalid Endpoint"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/invalid_endpoint")
check_response "GET /api/operations/invalid_endpoint (should 404)" "$response" "404"

# Invalid Query Parameters
print_test "Error Handling: Invalid Query Parameters (negative limit)"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/operations/dlq/items?limit=-1")
# Should return 422 (validation error) or handle gracefully
status_code=$(echo "$response" | grep -oP 'HTTP_STATUS:\K\d+' || echo "000")
if [ "$status_code" = "422" ] || [ "$status_code" = "400" ]; then
    echo -e "${GREEN}✓${NC} Invalid query parameters handled correctly (Status $status_code)"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠${NC} Unexpected status for invalid query: $status_code"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Tests Passed: ${TESTS_PASSED}${NC}"
echo -e "${RED}Tests Failed: ${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi

