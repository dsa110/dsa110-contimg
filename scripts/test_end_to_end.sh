#!/bin/bash
# End-to-end test script for data registry system

set -e

echo "=== End-to-End Data Registry Test ==="
echo ""

# 1. Test database migration
echo "1. Testing database migration..."
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning -c "
from dsa110_contimg.database.schema_evolution import evolve_products_schema
from pathlib import Path
import tempfile

db_path = Path('/data/dsa110-contimg/state/products.sqlite3')
if db_path.exists():
    result = evolve_products_schema(db_path, verbose=False)
    print(f'   Migration: {\"✓\" if result else \"✗\"}')
else:
    print('   ⚠ Database does not exist, skipping migration')
"
echo ""

# 2. Test data registration
echo "2. Testing data registration..."
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning scripts/test_data_registry.py
echo ""

# 3. Test API endpoints
echo "3. Testing API endpoints..."
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning -c "
from dsa110_contimg.api.routes import create_app
from fastapi.testclient import TestClient

app = create_app()
client = TestClient(app)

# Test list endpoint
response = client.get('/api/data')
assert response.status_code == 200, f'Expected 200, got {response.status_code}'
print(f'   GET /api/data: ✓ ({len(response.json())} instances)')

# Test with filters
response = client.get('/api/data?status=staging')
assert response.status_code == 200
print(f'   GET /api/data?status=staging: ✓')

print('   ✓ All API endpoints working')
"
echo ""

# 4. Check directory structure
echo "4. Checking directory structure..."
if [ -d "/stage/dsa110-contimg" ]; then
    echo "   ✓ /stage/dsa110-contimg exists"
else
    echo "   ✗ /stage/dsa110-contimg missing"
fi

if [ -d "/data/dsa110-contimg/products" ]; then
    echo "   ✓ /data/dsa110-contimg/products exists"
else
    echo "   ✗ /data/dsa110-contimg/products missing"
fi
echo ""

echo "=== Test Complete ==="
