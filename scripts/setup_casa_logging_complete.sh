#!/bin/bash
"""
Complete CASA Logging Setup

This script sets up a comprehensive CASA logging solution that ensures
all CASA log files are saved to the casalogs directory.
"""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CASALOGS_DIR="$PROJECT_ROOT/casalogs"

echo "Setting up complete CASA logging solution..."
echo "Project root: $PROJECT_ROOT"
echo "CASA logs directory: $CASALOGS_DIR"

# Ensure casalogs directory exists
mkdir -p "$CASALOGS_DIR"

# 1. Move any existing CASA log files from root to casalogs
echo "Step 1: Moving existing CASA log files..."
python "$SCRIPT_DIR/move_casa_logs.py"

# 2. Set up environment variables
echo "Step 2: Setting up environment variables..."
export CASA_LOG_DIR="$CASALOGS_DIR"
export CASA_LOG_FILE="$CASALOGS_DIR/casa.log"

# 3. Create CASA configuration
echo "Step 3: Creating CASA configuration..."
CASA_CONFIG_DIR="$PROJECT_ROOT/.casa"
mkdir -p "$CASA_CONFIG_DIR"

cat > "$CASA_CONFIG_DIR/rc" << EOF
# CASA configuration for DSA-110 pipeline
# Log directory: $CASALOGS_DIR
logfile = '$CASALOGS_DIR/casa.log'
logdir = '$CASALOGS_DIR'
EOF

# 4. Set up cron job for monitoring
echo "Step 4: Setting up cron job for monitoring..."
CRON_ENTRY="*/1 * * * * cd $PROJECT_ROOT && python $SCRIPT_DIR/casa_log_poller.py >> $PROJECT_ROOT/logs/casa_log_poller.log 2>&1"

# Add to crontab (only if not already present)
if ! crontab -l 2>/dev/null | grep -q "casa_log_poller.py"; then
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "Cron job added successfully!"
else
    echo "Cron job already exists"
fi

# 5. Create a startup script
echo "Step 5: Creating startup script..."
cat > "$PROJECT_ROOT/start_casa_logging.sh" << EOF
#!/bin/bash
# Start CASA logging monitoring

# Set environment variables
export CASA_LOG_DIR="$CASALOGS_DIR"
export CASA_LOG_FILE="$CASALOGS_DIR/casa.log"

# Start the poller
cd "$PROJECT_ROOT"
python "$SCRIPT_DIR/casa_log_poller.py" --daemon
EOF

chmod +x "$PROJECT_ROOT/start_casa_logging.sh"

# 6. Show status
echo ""
echo "CASA logging setup complete!"
echo ""
echo "Status:"
echo "  CASA logs directory: $CASALOGS_DIR"
echo "  Log files in casalogs: $(ls -1 "$CASALOGS_DIR"/*.log 2>/dev/null | wc -l)"
echo "  Log files in root: $(ls -1 "$PROJECT_ROOT"/casa-*.log 2>/dev/null | wc -l)"
echo ""
echo "Usage:"
echo "  Start monitoring: $PROJECT_ROOT/start_casa_logging.sh"
echo "  One-time cleanup: python $SCRIPT_DIR/move_casa_logs.py"
echo "  Manual poller: python $SCRIPT_DIR/casa_log_poller.py --daemon"
echo ""
echo "Cron job will run every minute to move any stray CASA log files."
