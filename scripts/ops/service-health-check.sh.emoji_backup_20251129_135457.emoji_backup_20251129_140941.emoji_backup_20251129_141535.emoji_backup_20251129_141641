#!/bin/bash
# service-health-check.sh - Comprehensive health checks for all DSA-110 services
# 
# This script validates that services are not just running, but actually functional.
# Run this BEFORE opening a browser or trusting that services are ready.
#
# Usage: ./service-health-check.sh [--verbose] [--json] [--service NAME]
#
# Exit codes:
#   0 - All services healthy
#   1 - One or more services unhealthy
#   2 - Script error

set -o pipefail

VERBOSE=false
JSON_OUTPUT=false
SINGLE_SERVICE=""
TIMEOUT=5

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v) VERBOSE=true; shift ;;
        --json|-j) JSON_OUTPUT=true; shift ;;
        --service|-s) SINGLE_SERVICE="$2"; shift 2 ;;
        --timeout|-t) TIMEOUT="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--verbose] [--json] [--service NAME] [--timeout SECS]"
            echo ""
            echo "Services: vite, fastapi, grafana, prometheus, redis, mkdocs"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 2 ;;
    esac
done

# Results storage
declare -A RESULTS
declare -A RESPONSE_TIMES
declare -A DETAILS
OVERALL_STATUS="healthy"

log() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "$1"
    fi
}

log_verbose() {
    if [[ "$VERBOSE" == "true" && "$JSON_OUTPUT" != "true" ]]; then
        echo -e "  ${BLUE}→${NC} $1"
    fi
}

# Check if port is listening
check_port_listening() {
    local port=$1
    ss -tln 2>/dev/null | grep -q ":${port} " && return 0 || return 1
}

# Generic HTTP health check with response validation
check_http() {
    local name=$1
    local port=$2
    local path=$3
    local expected_content=$4
    local start_time end_time response http_code body
    
    start_time=$(date +%s%N)
    
    # First check if port is listening
    if ! check_port_listening "$port"; then
        RESULTS[$name]="failed"
        DETAILS[$name]="Port $port not listening"
        return 1
    fi
    
    log_verbose "Port $port is listening"
    
    # Try to fetch the endpoint
    response=$(curl -s -w "\n%{http_code}" --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" \
        "http://127.0.0.1:${port}${path}" 2>&1) || {
        RESULTS[$name]="failed"
        DETAILS[$name]="Connection failed or timed out"
        return 1
    }
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    end_time=$(date +%s%N)
    RESPONSE_TIMES[$name]=$(( (end_time - start_time) / 1000000 ))
    
    log_verbose "HTTP $http_code in ${RESPONSE_TIMES[$name]}ms"
    
    # Check HTTP status
    if [[ ! "$http_code" =~ ^2[0-9][0-9]$ ]]; then
        RESULTS[$name]="failed"
        DETAILS[$name]="HTTP $http_code (expected 2xx)"
        return 1
    fi
    
    # Check expected content if provided
    if [[ -n "$expected_content" ]]; then
        if echo "$body" | grep -q "$expected_content"; then
            log_verbose "Content validation passed"
        else
            RESULTS[$name]="degraded"
            DETAILS[$name]="Response missing expected content: $expected_content"
            return 1
        fi
    fi
    
    RESULTS[$name]="healthy"
    DETAILS[$name]="OK (${RESPONSE_TIMES[$name]}ms)"
    return 0
}

# Check Redis with actual PING command
check_redis() {
    local port=6379
    local start_time end_time response
    
    start_time=$(date +%s%N)
    
    if ! check_port_listening "$port"; then
        RESULTS[redis]="failed"
        DETAILS[redis]="Port $port not listening"
        return 1
    fi
    
    log_verbose "Port $port is listening"
    
    # Send PING command to Redis
    response=$(echo "PING" | timeout "$TIMEOUT" nc -q1 127.0.0.1 "$port" 2>/dev/null) || {
        RESULTS[redis]="failed"
        DETAILS[redis]="Failed to connect to Redis"
        return 1
    }
    
    end_time=$(date +%s%N)
    RESPONSE_TIMES[redis]=$(( (end_time - start_time) / 1000000 ))
    
    log_verbose "Response: $response in ${RESPONSE_TIMES[redis]}ms"
    
    if [[ "$response" == *"PONG"* ]]; then
        RESULTS[redis]="healthy"
        DETAILS[redis]="PONG (${RESPONSE_TIMES[redis]}ms)"
        return 0
    else
        RESULTS[redis]="failed"
        DETAILS[redis]="Unexpected response: $response"
        return 1
    fi
}

# Check Vite dev server with HMR WebSocket validation
check_vite() {
    local port=3000
    
    # Basic HTTP check for index.html
    if ! check_http "vite" "$port" "/" "root"; then
        return 1
    fi
    
    # Additional check: Vite client script should be present
    local response
    response=$(curl -s --connect-timeout "$TIMEOUT" "http://127.0.0.1:${port}/" 2>/dev/null)
    
    if echo "$response" | grep -q "@vite/client"; then
        log_verbose "Vite HMR client detected"
        DETAILS[vite]="OK with HMR (${RESPONSE_TIMES[vite]}ms)"
    else
        DETAILS[vite]="Running but HMR may not work (${RESPONSE_TIMES[vite]}ms)"
        RESULTS[vite]="degraded"
    fi
    
    return 0
}

# Check FastAPI with health endpoint and OpenAPI validation
check_fastapi() {
    local port=8000
    
    # Check health endpoint
    if ! check_http "fastapi" "$port" "/api/health" "status"; then
        return 1
    fi
    
    log_verbose "Health endpoint OK"
    
    # Also verify OpenAPI docs are accessible (ensures routing works)
    local docs_response
    docs_response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$TIMEOUT" \
        "http://127.0.0.1:${port}/api/docs" 2>/dev/null)
    
    if [[ "$docs_response" == "200" ]]; then
        log_verbose "OpenAPI docs accessible"
        DETAILS[fastapi]="OK with OpenAPI (${RESPONSE_TIMES[fastapi]}ms)"
    else
        DETAILS[fastapi]="Health OK but docs unavailable (${RESPONSE_TIMES[fastapi]}ms)"
        RESULTS[fastapi]="degraded"
    fi
    
    return 0
}

# Check Grafana with login page validation
check_grafana() {
    local port=3030
    
    if ! check_http "grafana" "$port" "/login" "Grafana"; then
        # Grafana might redirect, try API endpoint
        if check_http "grafana" "$port" "/api/health" "ok"; then
            return 0
        fi
        return 1
    fi
    
    return 0
}

# Check Prometheus with targets validation
check_prometheus() {
    local port=9090
    
    # Check basic UI
    if ! check_http "prometheus" "$port" "/-/healthy" "Prometheus"; then
        # Fallback to root
        if ! check_http "prometheus" "$port" "/" "Prometheus"; then
            return 1
        fi
    fi
    
    # Check that scrape targets are configured
    local targets_response
    targets_response=$(curl -s --connect-timeout "$TIMEOUT" \
        "http://127.0.0.1:${port}/api/v1/targets" 2>/dev/null)
    
    if echo "$targets_response" | grep -q '"health":"up"'; then
        log_verbose "Scrape targets are up"
        DETAILS[prometheus]="OK with active targets (${RESPONSE_TIMES[prometheus]}ms)"
    elif echo "$targets_response" | grep -q '"activeTargets"'; then
        log_verbose "Targets configured but may be down"
        DETAILS[prometheus]="OK but some targets may be down (${RESPONSE_TIMES[prometheus]}ms)"
    fi
    
    return 0
}

# Check MkDocs
check_mkdocs() {
    local port=8001
    
    # MkDocs is optional, so mark as skipped if not running
    if ! check_port_listening "$port"; then
        RESULTS[mkdocs]="skipped"
        DETAILS[mkdocs]="Not running (optional dev service)"
        return 0
    fi
    
    check_http "mkdocs" "$port" "/" "MkDocs"
    return $?
}

# Run all checks
run_all_checks() {
    local services=("vite" "fastapi" "grafana" "prometheus" "redis" "mkdocs")
    
    if [[ -n "$SINGLE_SERVICE" ]]; then
        services=("$SINGLE_SERVICE")
    fi
    
    for service in "${services[@]}"; do
        log "${BLUE}Checking ${service}...${NC}"
        
        case $service in
            vite) check_vite ;;
            fastapi) check_fastapi ;;
            grafana) check_grafana ;;
            prometheus) check_prometheus ;;
            redis) check_redis ;;
            mkdocs) check_mkdocs ;;
            *)
                log "${YELLOW}Unknown service: $service${NC}"
                continue
                ;;
        esac
        
        # Update overall status
        case ${RESULTS[$service]} in
            failed) OVERALL_STATUS="unhealthy" ;;
            degraded) [[ "$OVERALL_STATUS" != "unhealthy" ]] && OVERALL_STATUS="degraded" ;;
        esac
    done
}

# Print results
print_results() {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo "{"
        echo '  "timestamp": "'$(date -Iseconds)'",'
        echo '  "overall_status": "'$OVERALL_STATUS'",'
        echo '  "services": {'
        local first=true
        for service in "${!RESULTS[@]}"; do
            [[ "$first" != "true" ]] && echo ","
            first=false
            echo -n "    \"$service\": {\"status\": \"${RESULTS[$service]}\", \"details\": \"${DETAILS[$service]}\""
            [[ -n "${RESPONSE_TIMES[$service]}" ]] && echo -n ", \"response_time_ms\": ${RESPONSE_TIMES[$service]}"
            echo -n "}"
        done
        echo ""
        echo "  }"
        echo "}"
    else
        echo ""
        log "═══════════════════════════════════════════════════════════"
        log "                    SERVICE HEALTH REPORT"
        log "═══════════════════════════════════════════════════════════"
        echo ""
        
        for service in vite fastapi grafana prometheus redis mkdocs; do
            [[ -z "${RESULTS[$service]}" ]] && continue
            
            local status_icon status_color
            case ${RESULTS[$service]} in
                healthy)  status_icon="✓"; status_color="$GREEN" ;;
                degraded) status_icon="◐"; status_color="$YELLOW" ;;
                failed)   status_icon="✗"; status_color="$RED" ;;
                skipped)  status_icon="○"; status_color="$BLUE" ;;
            esac
            
            printf "  ${status_color}%s${NC} %-12s %s\n" "$status_icon" "$service" "${DETAILS[$service]}"
        done
        
        echo ""
        log "───────────────────────────────────────────────────────────"
        
        case $OVERALL_STATUS in
            healthy)
                log "${GREEN}✓ All services healthy - safe to open browser${NC}"
                ;;
            degraded)
                log "${YELLOW}◐ Some services degraded - browser may work with issues${NC}"
                ;;
            unhealthy)
                log "${RED}✗ Services unhealthy - DO NOT trust browser access${NC}"
                log ""
                log "  Run: ${BLUE}sudo systemctl status <service>${NC} for details"
                log "  Or:  ${BLUE}sudo journalctl -u <service> -n 20${NC} for logs"
                ;;
        esac
        
        echo ""
    fi
}

# Main
log ""
log "${BLUE}DSA-110 Service Health Check${NC}"
log "$(date)"
log ""

run_all_checks
print_results

# Exit with appropriate code
case $OVERALL_STATUS in
    healthy) exit 0 ;;
    degraded) exit 0 ;;  # Degraded is still usable
    unhealthy) exit 1 ;;
esac
