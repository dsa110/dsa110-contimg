#!/bin/bash
# Test script for DSA-110 Continuum Imaging Pipeline API

BASE_URL="http://localhost:8000/api"
PASS="\033[0;32m:check: PASS\033[0m"
FAIL="\033[0;31m:cross: FAIL\033[0m"

echo "========================================="
echo "Testing DSA-110 Continuum Imaging API"
echo "========================================="
echo

# Helper function to test endpoint
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="$3"
    
    response=$(curl -s -w "\n%{http_code}" "$url")
    status=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$status" -eq "$expected_status" ]; then
        echo -e "$PASS $name (status: $status)"
        return 0
    else
        echo -e "$FAIL $name (expected: $expected_status, got: $status)"
        echo "  Response: $body" | head -n 3
        return 1
    fi
}

# 1. Health check
echo "1. Health Check"
test_endpoint "Health endpoint" "$BASE_URL/health" 200
echo

# 2. MS endpoints
echo "2. Measurement Set Endpoints"
MS_PATH="/stage/dsa110-contimg/ms/2025-10-31T13:49:06.ms"
ENCODED_MS=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$MS_PATH', safe=''))")
test_endpoint "MS metadata" "$BASE_URL/ms/$ENCODED_MS/metadata" 200
test_endpoint "MS calibrator matches" "$BASE_URL/ms/$ENCODED_MS/calibrator-matches" 200
test_endpoint "MS not found (404)" "$BASE_URL/ms/notfound.ms/metadata" 404
echo

# 3. Source endpoints
echo "3. Source Endpoints"
test_endpoint "Source detail" "$BASE_URL/sources/J1293249+525013" 200
test_endpoint "Source not found (404)" "$BASE_URL/sources/notfound" 404
echo

# 4. Job/Provenance endpoints
echo "4. Job/Provenance Endpoints"
RUN_ID="job-2025-10-31-134906"
test_endpoint "Job provenance" "$BASE_URL/jobs/$RUN_ID/provenance" 200
test_endpoint "Job logs" "$BASE_URL/jobs/$RUN_ID/logs?tail=5" 200
echo

# 5. QA endpoints
echo "5. QA Endpoints"
test_endpoint "QA job" "$BASE_URL/qa/job/$RUN_ID" 200
test_endpoint "QA MS" "$BASE_URL/qa/ms/$ENCODED_MS" 200
echo

# 6. Calibration endpoints
echo "6. Calibration Endpoints"
CAL_PATH="/stage/dsa110-contimg/ms/0834_lightcurve/0834_2025-10-25T14-11-19_0~23_2gcal"
ENCODED_CAL=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$CAL_PATH', safe=''))")
test_endpoint "Cal table detail" "$BASE_URL/cal/$ENCODED_CAL" 200
test_endpoint "Cal table not found (404)" "$BASE_URL/cal/notfound.cal" 404
echo

# 7. Logs endpoints (alternative path)
echo "7. Logs Endpoints (Alternative)"
test_endpoint "Logs endpoint" "$BASE_URL/logs/$RUN_ID?tail=5" 200
echo

# 8. Image endpoints (if any images exist)
echo "8. Image Endpoints"
test_endpoint "Image not found (404)" "$BASE_URL/images/999999" 404
echo

echo "========================================="
echo "API Tests Complete"
echo "========================================="
