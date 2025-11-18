#!/bin/bash
# Production deployment script for calibrators.sqlite3 migration
# This script performs the migration and verifies the system is ready for production use.

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Calibrators.sqlite3 Migration Deployment ===${NC}"
echo ""

# Configuration
PRODUCTS_DB="${PRODUCTS_DB:-state/products.sqlite3}"
CALIBRATORS_DB="${CALIBRATORS_DB:-state/calibrators.sqlite3}"
PYTHON_ENV="${PYTHON_ENV:-/opt/miniforge/envs/casa6/bin/python}"

# Step 1: Verify prerequisites
echo -e "${YELLOW}Step 1: Verifying prerequisites...${NC}"
if [ ! -f "$PRODUCTS_DB" ]; then
    echo -e "${RED}ERROR: Products database not found: $PRODUCTS_DB${NC}"
    exit 1
fi

if [ ! -f "$PYTHON_ENV" ]; then
    echo -e "${RED}ERROR: Python environment not found: $PYTHON_ENV${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites verified${NC}"
echo ""

# Step 2: Backup existing databases
echo -e "${YELLOW}Step 2: Creating backups...${NC}"
BACKUP_DIR="state/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "$PRODUCTS_DB" ]; then
    cp "$PRODUCTS_DB" "$BACKUP_DIR/products.sqlite3.backup"
    echo -e "${GREEN}✓ Backed up products.sqlite3${NC}"
fi

if [ -f "$CALIBRATORS_DB" ]; then
    cp "$CALIBRATORS_DB" "$BACKUP_DIR/calibrators.sqlite3.backup"
    echo -e "${GREEN}✓ Backed up calibrators.sqlite3${NC}"
fi

echo ""

# Step 3: Run migration (dry-run first)
echo -e "${YELLOW}Step 3: Running migration (dry-run)...${NC}"
$PYTHON_ENV src/dsa110_contimg/database/migrate_calibrators.py \
    --products-db "$PRODUCTS_DB" \
    --calibrators-db "$CALIBRATORS_DB" \
    --dry-run

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Dry-run migration failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dry-run successful${NC}"
echo ""

# Step 4: Run actual migration
echo -e "${YELLOW}Step 4: Running actual migration...${NC}"
$PYTHON_ENV src/dsa110_contimg/database/migrate_calibrators.py \
    --products-db "$PRODUCTS_DB" \
    --calibrators-db "$CALIBRATORS_DB"

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Migration failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Migration completed${NC}"
echo ""

# Step 5: Verify migration
echo -e "${YELLOW}Step 5: Verifying migration...${NC}"
$PYTHON_ENV -c "
import sqlite3
from pathlib import Path

products_db = Path('$PRODUCTS_DB')
calibrators_db = Path('$CALIBRATORS_DB')

# Count in products.sqlite3
if products_db.exists():
    conn = sqlite3.connect(products_db)
    try:
        cursor = conn.execute('SELECT COUNT(*) FROM bandpass_calibrators')
        products_count = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        products_count = 0
    conn.close()
else:
    products_count = 0

# Count in calibrators.sqlite3
if calibrators_db.exists():
    conn = sqlite3.connect(calibrators_db)
    cursor = conn.execute('SELECT COUNT(*) FROM bandpass_calibrators')
    calibrators_count = cursor.fetchone()[0]
    conn.close()
else:
    calibrators_count = 0

print(f'Products DB: {products_count} calibrators')
print(f'Calibrators DB: {calibrators_count} calibrators')

if calibrators_count > 0:
    print('✓ Migration verified: Calibrators found in new database')
else:
    print('⚠ No calibrators migrated (database may have been empty)')
"

echo ""

# Step 6: Run integration tests
echo -e "${YELLOW}Step 6: Running integration tests...${NC}"
$PYTHON_ENV -m pytest tests/integration/test_calibrators_integration.py -v --tb=short

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Integration tests failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Integration tests passed${NC}"
echo ""

# Step 7: Run unit tests
echo -e "${YELLOW}Step 7: Running unit tests...${NC}"
$PYTHON_ENV -m pytest tests/database/test_calibrators_db.py tests/database/test_catalog_query.py tests/database/test_skymodel_storage.py -v --tb=short

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Unit tests failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Unit tests passed${NC}"
echo ""

# Step 8: Verify database schema
echo -e "${YELLOW}Step 8: Verifying database schema...${NC}"
$PYTHON_ENV -c "
from dsa110_contimg.database.calibrators import ensure_calibrators_db
from pathlib import Path
import sqlite3

calibrators_db = Path('$CALIBRATORS_DB')
conn = ensure_calibrators_db(calibrators_db)

cursor = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
tables = {row[0] for row in cursor.fetchall()}

required_tables = {
    'bandpass_calibrators',
    'gain_calibrators',
    'catalog_sources',
    'vla_calibrators',
    'vla_flux_info',
    'skymodel_metadata'
}

missing = required_tables - tables
if missing:
    print(f'ERROR: Missing tables: {missing}')
    exit(1)
else:
    print('✓ All required tables present')

conn.close()
"

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Schema verification failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Schema verified${NC}"
echo ""

# Summary
echo -e "${GREEN}=== Deployment Summary ===${NC}"
echo "Backup location: $BACKUP_DIR"
echo "Products DB: $PRODUCTS_DB"
echo "Calibrators DB: $CALIBRATORS_DB"
echo ""
echo -e "${GREEN}✓ Migration deployment completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Monitor pipeline logs for any issues"
echo "  2. Verify calibrator queries work in production"
echo "  3. Test skymodel creation with real data"

