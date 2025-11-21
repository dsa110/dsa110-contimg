#!/bin/bash
# Setup script for Absurd integration
# This script sets up the Absurd database schema and creates the initial queue

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Absurd Setup Script${NC}"
echo "===================="
echo ""

# Check if PostgreSQL is available
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql not found. Please install PostgreSQL client.${NC}"
    exit 1
fi

# Get database connection info
read -p "Database name [dsa110_absurd]: " DB_NAME
DB_NAME=${DB_NAME:-dsa110_absurd}

read -p "Database host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "Database port [5432]: " DB_PORT
DB_PORT=${DB_PORT:-5432}

read -p "Database user [postgres]: " DB_USER
DB_USER=${DB_USER:-postgres}

read -s -p "Database password: " DB_PASSWORD
echo ""

# Construct connection string
export PGPASSWORD="$DB_PASSWORD"
PSQL_CMD="psql -h $DB_HOST -p $DB_PORT -U $DB_USER"

# Check if database exists, create if not
echo -e "${YELLOW}Checking database...${NC}"
if $PSQL_CMD -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo -e "${GREEN}Database '$DB_NAME' exists${NC}"
else
    echo -e "${YELLOW}Creating database '$DB_NAME'...${NC}"
    $PSQL_CMD -c "CREATE DATABASE $DB_NAME;"
    echo -e "${GREEN}Database created${NC}"
fi

# Install Absurd schema
echo -e "${YELLOW}Installing Absurd schema...${NC}"
ABSURD_SQL="/home/ubuntu/proj/absurd/sql/absurd.sql"

if [ ! -f "$ABSURD_SQL" ]; then
    echo -e "${RED}Error: Absurd SQL file not found at $ABSURD_SQL${NC}"
    echo "Please ensure Absurd is installed at /home/ubuntu/proj/absurd/"
    exit 1
fi

$PSQL_CMD -d "$DB_NAME" -f "$ABSURD_SQL"
echo -e "${GREEN}Schema installed${NC}"

# Create queue
echo -e "${YELLOW}Creating queue 'dsa110-pipeline'...${NC}"
$PSQL_CMD -d "$DB_NAME" -c "SELECT absurd.create_queue('dsa110-pipeline');"
echo -e "${GREEN}Queue created${NC}"

# Verify installation
echo -e "${YELLOW}Verifying installation...${NC}"
QUEUE_COUNT=$($PSQL_CMD -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM absurd.queues WHERE queue_name = 'dsa110-pipeline';" | tr -d ' ')

if [ "$QUEUE_COUNT" = "1" ]; then
    echo -e "${GREEN}✓ Installation verified${NC}"
else
    echo -e "${RED}✗ Verification failed${NC}"
    exit 1
fi

# Generate connection string
CONNECTION_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Add these environment variables:"
echo "  export ABSURD_ENABLED=true"
echo "  export ABSURD_DATABASE_URL=\"$CONNECTION_URL\""
echo "  export ABSURD_QUEUE_NAME=dsa110-pipeline"
echo ""
echo "Or add to your .env file:"
echo "  ABSURD_ENABLED=true"
echo "  ABSURD_DATABASE_URL=$CONNECTION_URL"
echo "  ABSURD_QUEUE_NAME=dsa110-pipeline"

