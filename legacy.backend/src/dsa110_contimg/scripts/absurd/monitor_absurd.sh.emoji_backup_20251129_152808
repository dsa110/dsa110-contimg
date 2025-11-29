#!/bin/bash
# Absurd Pipeline Monitoring Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/data/dsa110-contimg"
DB_URL="${ABSURD_DATABASE_URL:-postgresql://user:password@localhost/dsa110_absurd}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         DSA-110 Absurd Pipeline Monitor                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check service status
check_service() {
    local service=$1
    if systemctl is-active --quiet "$service"; then
        echo -e "${GREEN}✓${NC} $service: ${GREEN}RUNNING${NC}"
        return 0
    else
        echo -e "${RED}✗${NC} $service: ${RED}STOPPED${NC}"
        return 1
    fi
}

# Check Services
echo -e "${YELLOW}=== Service Status ===${NC}"
check_service "dsa110-absurd-worker@1.service"
check_service "dsa110-mosaic-daemon.service"
echo ""

# Check Worker Count
echo -e "${YELLOW}=== Active Workers ===${NC}"
WORKER_COUNT=$(systemctl list-units --state=active | grep "dsa110-absurd-worker@" | wc -l)
echo "Active workers: $WORKER_COUNT"
echo ""

# Query Database Statistics
echo -e "${YELLOW}=== Task Queue Statistics ===${NC}"
export PGPASSWORD="password"
psql -h localhost -U user -d dsa110_absurd -t -A -c "
SELECT 
    status,
    COUNT(*) as count
FROM absurd.t_tasks 
GROUP BY status 
ORDER BY status;
" 2>/dev/null | while IFS='|' read -r status count; do
    if [ -n "$status" ]; then
        case "$status" in
            completed)
                echo -e "  Completed: ${GREEN}$count${NC}"
                ;;
            failed)
                echo -e "  Failed: ${RED}$count${NC}"
                ;;
            claimed)
                echo -e "  Running: ${YELLOW}$count${NC}"
                ;;
            pending)
                echo -e "  Pending: ${BLUE}$count${NC}"
                ;;
            *)
                echo -e "  $status: $count"
                ;;
        esac
    fi
done || echo -e "${RED}  Unable to connect to database${NC}"
echo ""

# Recent Task Activity
echo -e "${YELLOW}=== Recent Task Activity (Last 10) ===${NC}"
psql -h localhost -U user -d dsa110_absurd -c "
SELECT 
    SUBSTRING(task_id::text, 1, 8) as task,
    task_name,
    status,
    worker_id,
    TO_CHAR(created_at, 'HH24:MI:SS') as created
FROM absurd.t_tasks 
ORDER BY created_at DESC 
LIMIT 10;
" 2>/dev/null || echo -e "${RED}  Unable to query database${NC}"
echo ""

# Check Disk Space
echo -e "${YELLOW}=== Disk Space ===${NC}"
df -h /data/incoming /stage/dsa110-contimg | tail -n +2 | while read -r line; do
    usage=$(echo "$line" | awk '{print $5}' | tr -d '%')
    if [ "$usage" -gt 90 ]; then
        echo -e "${RED}$line${NC}"
    elif [ "$usage" -gt 80 ]; then
        echo -e "${YELLOW}$line${NC}"
    else
        echo -e "${GREEN}$line${NC}"
    fi
done
echo ""

# Recent Logs
echo -e "${YELLOW}=== Recent Worker Logs (Last 5 lines) ===${NC}"
journalctl -u dsa110-absurd-worker@1 -n 5 --no-pager --since "5 minutes ago" 2>/dev/null || echo "No recent logs"
echo ""

echo -e "${YELLOW}=== Recent Daemon Logs (Last 5 lines) ===${NC}"
journalctl -u dsa110-mosaic-daemon -n 5 --no-pager --since "5 minutes ago" 2>/dev/null || echo "No recent logs"
echo ""

# Usage Instructions
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Monitoring Commands:${NC}"
echo -e "  Worker logs:  ${GREEN}sudo journalctl -u dsa110-absurd-worker@1 -f${NC}"
echo -e "  Daemon logs:  ${GREEN}sudo journalctl -u dsa110-mosaic-daemon -f${NC}"
echo -e "  Both logs:    ${GREEN}sudo journalctl -u 'dsa110-absurd-*' -f${NC}"
echo -e ""
echo -e "${BLUE}Management Commands:${NC}"
echo -e "  Restart worker:  ${YELLOW}sudo systemctl restart dsa110-absurd-worker@1${NC}"
echo -e "  Restart daemon:  ${YELLOW}sudo systemctl restart dsa110-mosaic-daemon${NC}"
echo -e "  Scale workers:   ${YELLOW}sudo systemctl start dsa110-absurd-worker@{2..4}${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
