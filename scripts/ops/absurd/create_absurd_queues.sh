#!/bin/bash
#
# Create Absurd queues for DSA-110 pipeline.
#
# This script creates the main pipeline queue in Absurd.

set -e  # Exit on error

# Configuration
DB_NAME="${ABSURD_DB_NAME:-dsa110_absurd}"
DB_USER="${ABSURD_DB_USER:-postgres}"
DB_HOST="${ABSURD_DB_HOST:-localhost}"
DB_PORT="${ABSURD_DB_PORT:-5432}"
QUEUE_NAME="${ABSURD_QUEUE_NAME:-dsa110-pipeline}"

echo "=== Absurd Queue Creation ==="
echo "Database: $DB_NAME"
echo "Queue: $QUEUE_NAME"
echo ""

# Check if queue already exists
EXISTING=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
    "SELECT COUNT(*) FROM absurd.queues WHERE queue_name = '$QUEUE_NAME';")

if [ "$EXISTING" -gt 0 ]; then
    echo "Queue '$QUEUE_NAME' already exists."
    exit 0
fi

# Create queue
echo "Creating queue '$QUEUE_NAME'..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
    "SELECT absurd.create_queue('$QUEUE_NAME');"

echo ":check: Queue created"
echo ""
echo "Verify with:"
echo "  psql -d $DB_NAME -c \"SELECT * FROM absurd.queues;\""
