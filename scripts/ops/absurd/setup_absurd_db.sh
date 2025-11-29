#!/bin/bash
#
# Setup script for Absurd database schema.
#
# This script creates the Absurd database and installs the schema.

set -e  # Exit on error

# Configuration
DB_NAME="${ABSURD_DB_NAME:-dsa110_absurd}"
DB_USER="${ABSURD_DB_USER:-postgres}"
DB_HOST="${ABSURD_DB_HOST:-localhost}"
DB_PORT="${ABSURD_DB_PORT:-5432}"
ABSURD_SQL_PATH="${ABSURD_SQL_PATH:-$HOME/proj/absurd/sql/absurd.sql}"

echo "=== Absurd Database Setup ==="
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo ""

# Check if PostgreSQL is available
if ! command -v psql &> /dev/null; then
    echo "ERROR: psql command not found. Please install PostgreSQL client."
    exit 1
fi

# Check if we can connect
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c '\q' 2>/dev/null; then
    echo "ERROR: Cannot connect to PostgreSQL at $DB_HOST:$DB_PORT as user $DB_USER"
    echo "Please ensure PostgreSQL is running and credentials are correct."
    exit 1
fi

echo ":check: PostgreSQL connection verified"

# Check if database exists
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "Database '$DB_NAME' already exists."
    read -p "Do you want to drop and recreate it? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy]es$ ]]; then
        echo "Dropping database..."
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;"
    else
        echo "Keeping existing database. Schema may be updated."
    fi
fi

# Create database if it doesn't exist
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "Creating database '$DB_NAME'..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;"
    echo ":check: Database created"
else
    echo ":check: Using existing database"
fi

# Install Absurd schema
if [ ! -f "$ABSURD_SQL_PATH" ]; then
    echo "ERROR: Absurd SQL file not found at: $ABSURD_SQL_PATH"
    echo "Please set ABSURD_SQL_PATH environment variable to the correct path."
    exit 1
fi

echo "Installing Absurd schema from: $ABSURD_SQL_PATH"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$ABSURD_SQL_PATH"
echo ":check: Schema installed"

# Verify installation
echo "Verifying installation..."
QUEUE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM absurd.queues;")
echo ":check: Absurd schema verified (queues table has $QUEUE_COUNT rows)"

# Print connection string
echo ""
echo "=== Setup Complete ==="
echo "Connection string:"
echo "  postgresql://$DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""
echo "Environment variable:"
echo "  export ABSURD_DATABASE_URL=\"postgresql://$DB_USER@$DB_HOST:$DB_PORT/$DB_NAME\""
echo ""
echo "Next steps:"
echo "  1. Create a queue: ./scripts/absurd/create_absurd_queues.sh"
echo "  2. Test connection: python scripts/absurd/test_absurd_connection.py"
