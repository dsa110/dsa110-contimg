#!/bin/bash
# Test Operations page using Chrome with remote debugging
# This allows us to inspect the page even if Playwright isn't available

set -e

FRONTEND_URL="http://localhost:5173/operations"
CHROME_USER_DATA_DIR="/tmp/chrome-test-$$"

echo "=========================================="
echo "Testing Operations Page with Chrome"
echo "=========================================="
echo ""

# Check if frontend is running
if ! curl -s -f "http://localhost:5173" > /dev/null 2>&1; then
    echo "Error: Frontend server is not running"
    exit 1
fi

echo "Frontend URL: ${FRONTEND_URL}"
echo ""
echo "Launching Chrome with remote debugging..."
echo "Chrome will open the Operations page"
echo "You can inspect it using Chrome DevTools"
echo ""

# Launch Chrome with remote debugging and open the page
google-chrome \
    --remote-debugging-port=9222 \
    --user-data-dir="${CHROME_USER_DATA_DIR}" \
    --no-first-run \
    --no-default-browser-check \
    "${FRONTEND_URL}" \
    > /dev/null 2>&1 &

CHROME_PID=$!
echo "Chrome launched (PID: ${CHROME_PID})"
echo "Remote debugging available at: http://localhost:9222"
echo ""
echo "Waiting 5 seconds for page to load..."
sleep 5

# Try to get page info via Chrome DevTools Protocol
echo "Attempting to connect to Chrome DevTools Protocol..."
cdp_response=$(curl -s "http://localhost:9222/json" 2>/dev/null || echo "[]")

if [ "$cdp_response" != "[]" ] && [ -n "$cdp_response" ]; then
    echo ":check: Connected to Chrome DevTools Protocol"
    page_count=$(echo "$cdp_response" | jq 'length' 2>/dev/null || echo "0")
    echo "  Found ${page_count} page(s)"
    
    # Get page title
    page_id=$(echo "$cdp_response" | jq -r '.[0].id' 2>/dev/null || echo "")
    if [ -n "$page_id" ]; then
        title_response=$(curl -s "http://localhost:9222/json/runtime/evaluate" \
            -H "Content-Type: application/json" \
            -d "{\"expression\": \"document.title\"}" 2>/dev/null || echo "")
        if [ -n "$title_response" ]; then
            title=$(echo "$title_response" | jq -r '.result.value' 2>/dev/null || echo "")
            echo "  Page title: ${title}"
        fi
    fi
else
    echo ":warning: Could not connect to Chrome DevTools Protocol"
    echo "  Chrome is running, but CDP connection failed"
    echo "  You can manually inspect the page in Chrome"
fi

echo ""
echo "Chrome browser is open with the Operations page"
echo "You can:"
echo "  1. Open Chrome DevTools (F12)"
echo "  2. Check the Network tab for API calls"
echo "  3. Inspect the Console for errors"
echo "  4. Verify UI components are rendering"
echo ""
echo "To close Chrome, press Ctrl+C or run:"
echo "  kill ${CHROME_PID}"
echo ""
echo "Waiting 30 seconds for manual inspection..."
sleep 30

# Cleanup
echo "Closing Chrome..."
kill ${CHROME_PID} 2>/dev/null || true
rm -rf "${CHROME_USER_DATA_DIR}" 2>/dev/null || true
echo "Done"

