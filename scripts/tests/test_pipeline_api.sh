#!/bin/bash
# Test script for pipeline monitoring API endpoints

set -e

API_BASE="${API_BASE:-http://localhost:8000}"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Pipeline API Endpoint Testing"
echo "=========================================="
echo ""

# Function to test an endpoint
test_endpoint() {
    local name="$1"
    local endpoint="$2"
    local expected_fields="$3"
    
    echo -n "Testing $name... "
    
    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}${endpoint}")
    http_code=$(echo "$response" | grep -oE 'HTTP_STATUS:([0-9]+)' | grep -oE '[0-9]+' || echo "000")
    body=$(echo "$response" | sed '/HTTP_STATUS:/d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓${NC} (HTTP $http_code)"
        
        # Check if response is valid JSON
        if echo "$body" | jq . > /dev/null 2>&1; then
            echo "  Response is valid JSON"
            
            # Check for expected fields if provided
            if [ -n "$expected_fields" ]; then
                for field in $expected_fields; do
                    if echo "$body" | jq -e ".$field" > /dev/null 2>&1; then
                        echo "  ✓ Contains field: $field"
                    else
                        echo -e "  ${YELLOW}⚠${NC} Missing field: $field"
                    fi
                done
            fi
            
            # Show preview
            echo "  Preview: $(echo "$body" | jq -c '.' | head -c 100)..."
        else
            echo -e "  ${YELLOW}⚠${NC} Response is not valid JSON"
            echo "  Response: $(echo "$body" | head -c 200)"
        fi
    else
        echo -e "${RED}✗${NC} (HTTP $http_code)"
        echo "  Response: $(echo "$body" | head -c 200)"
    fi
    echo ""
}

# Test endpoints
echo "1. Testing Pipeline Executions Endpoints"
echo "----------------------------------------"
test_endpoint "List Executions" "/api/pipeline/executions?limit=10" "length"
test_endpoint "Active Executions" "/api/pipeline/executions/active" "length"

# Get first execution ID if available
EXECUTIONS_RESPONSE=$(curl -s "${API_BASE}/api/pipeline/executions?limit=1")
EXECUTION_ID=$(echo "$EXECUTIONS_RESPONSE" | jq -r 'if type == "array" and length > 0 then .[0].id else empty end' 2>/dev/null || echo "")

if [ -n "$EXECUTION_ID" ] && [ "$EXECUTION_ID" != "null" ] && [ "$EXECUTION_ID" != "" ]; then
    echo "Found execution ID: $EXECUTION_ID"
    test_endpoint "Execution Details" "/api/pipeline/executions/${EXECUTION_ID}" "id status job_type"
    test_endpoint "Execution Stages" "/api/pipeline/executions/${EXECUTION_ID}/stages" "length"
else
    echo -e "${YELLOW}⚠${NC} No executions found for detail testing"
    echo ""
fi

echo ""
echo "2. Testing Stage Metrics Endpoints"
echo "----------------------------------------"
test_endpoint "Stage Metrics" "/api/pipeline/stages/metrics" "length"
test_endpoint "Stage Metrics (catalog_setup)" "/api/pipeline/stages/catalog_setup/metrics" "stage_name total_executions"

echo ""
echo "3. Testing Dependency Graph"
echo "----------------------------------------"
test_endpoint "Dependency Graph" "/api/pipeline/dependency-graph" "nodes edges"

echo ""
echo "4. Testing Metrics Summary"
echo "----------------------------------------"
test_endpoint "Metrics Summary" "/api/pipeline/metrics/summary" "total_jobs running_jobs completed_jobs"

echo ""
echo "=========================================="
echo "Testing Complete"
echo "=========================================="

