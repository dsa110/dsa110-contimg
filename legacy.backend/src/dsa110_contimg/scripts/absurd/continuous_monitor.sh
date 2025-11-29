#!/bin/bash
# Continuous Absurd Pipeline Monitor
# Displays real-time updates in a watch-style interface

REFRESH_INTERVAL=5  # seconds
LOG_FILE="/tmp/absurd_monitor.log"

# Trap Ctrl+C for clean exit
trap 'echo -e "\n\n:check_mark: Monitor stopped."; exit 0' INT TERM

echo "Starting Absurd Continuous Monitor (refresh every ${REFRESH_INTERVAL}s)"
echo "Press Ctrl+C to stop"
echo "Logging to: $LOG_FILE"
echo ""

while true; do
    clear
    {
        echo "════════════════════════════════════════════════════════════"
        echo "  DSA-110 Absurd Pipeline - Live Monitor"
        echo "  $(date '+%Y-%m-%d %H:%M:%S')"
        echo "════════════════════════════════════════════════════════════"
        echo ""
        
        # Service status
        echo "【 SERVICE STATUS 】"
        systemctl is-active --quiet dsa110-mosaic-daemon && \
            echo "  :check_mark: Daemon: RUNNING" || echo "  :ballot_x: Daemon: STOPPED"
        
        WORKER_COUNT=$(systemctl list-units --state=active 'dsa110-absurd-worker@*' 2>/dev/null | grep -c "dsa110-absurd-worker")
        echo "  :check_mark: Workers: $WORKER_COUNT active"
        echo ""
        
        # Queue statistics
        echo "【 QUEUE STATISTICS 】"
        export PGPASSWORD="password"
        psql -h localhost -U user -d dsa110_absurd -t -A -c "
            SELECT 
                COALESCE(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END), 0) as pending,
                COALESCE(SUM(CASE WHEN status = 'claimed' THEN 1 ELSE 0 END), 0) as running,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) as completed,
                COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) as failed
            FROM absurd.t_tasks 
            WHERE created_at > NOW() - INTERVAL '1 hour';
        " 2>/dev/null | {
            IFS='|' read -r pending running completed failed
            echo "  Pending:   $pending"
            echo "  Running:   $running"
            echo "  Completed: $completed (last hour)"
            echo "  Failed:    $failed (last hour)"
        }
        echo ""
        
        # Recent activity
        echo "【 RECENT TASKS (Last 5) 】"
        psql -h localhost -U user -d dsa110_absurd -t -A -F ' | ' -c "
            SELECT 
                TO_CHAR(created_at, 'HH24:MI:SS') as time,
                SUBSTRING(task_name, 1, 18) as task,
                status,
                COALESCE(SUBSTRING(worker_id, 1, 15), '-') as worker
            FROM absurd.t_tasks 
            ORDER BY created_at DESC 
            LIMIT 5;
        " 2>/dev/null | while IFS='|' read -r time task status worker; do
            echo "  $time | $task | $status | $worker"
        done || echo "  (No database connection)"
        echo ""
        
        # System resources
        echo "【 SYSTEM RESOURCES 】"
        # CPU load
        LOAD=$(uptime | awk -F'load average:' '{ print $2 }' | awk '{ print $1 }' | tr -d ',')
        echo "  Load avg: $LOAD"
        
        # Memory
        free -h | grep Mem | awk '{printf "  Memory:   %s / %s used\n", $3, $2}'
        
        # Disk space
        df -h /data/incoming /stage/dsa110-contimg 2>/dev/null | tail -n +2 | while read -r line; do
            fs=$(echo "$line" | awk '{print $6}')
            used=$(echo "$line" | awk '{print $5}')
            avail=$(echo "$line" | awk '{print $4}')
            echo "  $fs: $used used ($avail free)"
        done
        echo ""
        
        # Recent logs (errors only)
        echo "【 RECENT ERRORS (Last 5 minutes) 】"
        ERROR_COUNT=$(journalctl -u 'dsa110-absurd-*' -u dsa110-mosaic-daemon \
            --since "5 minutes ago" --no-pager -p err 2>/dev/null | grep -c "ERROR" || echo "0")
        
        if [ "$ERROR_COUNT" -gt 0 ]; then
            echo "  :warning_sign: $ERROR_COUNT errors detected"
            journalctl -u 'dsa110-absurd-*' -u dsa110-mosaic-daemon \
                --since "5 minutes ago" --no-pager -p err 2>/dev/null | tail -3
        else
            echo "  :check_mark: No errors in last 5 minutes"
        fi
        echo ""
        
        echo "════════════════════════════════════════════════════════════"
        echo "  Next refresh in ${REFRESH_INTERVAL}s | Ctrl+C to exit"
        echo "════════════════════════════════════════════════════════════"
        
    } | tee "$LOG_FILE"
    
    sleep "$REFRESH_INTERVAL"
done
