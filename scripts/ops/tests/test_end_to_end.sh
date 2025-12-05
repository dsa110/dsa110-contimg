#!/bin/bash
# End-to-end test script for data registry system

set -e

echo "=== End-to-End Data Registry Test ==="
echo ""

# 1. Test database initialization
echo "1. Testing database initialization..."
PYTHONPATH=/data/dsa110-contimg/backend/src /opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning -c "
from dsa110_contimg.database import ensure_pipeline_db

conn = ensure_pipeline_db()
tables = [row[0] for row in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
conn.close()
print(f'   Database initialized: ✓ ({len(tables)} tables)')
"
echo ""

# 2. Test data registration
echo "2. Testing data registration..."
PYTHONPATH=/data/dsa110-contimg/backend/src /opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning scripts/test_data_registry.py
echo ""

# 3. Test API endpoints
echo "3. Testing API endpoints..."
PYTHONPATH=/data/dsa110-contimg/backend/src /opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning -c "
from dsa110_contimg.api.routes import create_app
from fastapi.testclient import TestClient

app = create_app()
client = TestClient(app)

# Test list endpoint
response = client.get('/api/data')
assert response.status_code == 200, f'Expected 200, got {response.status_code}'
print(f'   GET /api/data: :check: ({len(response.json())} instances)')

# Test with filters
response = client.get('/api/data?status=staging')
assert response.status_code == 200
print(f'   GET /api/data?status=staging: :check:')

print('   :check: All API endpoints working')
"
echo ""

# 4. Check directory structure
echo "4. Checking directory structure..."
if [ -d "/stage/dsa110-contimg" ]; then
    echo "   :check: /stage/dsa110-contimg exists"
else
    echo "   :cross: /stage/dsa110-contimg missing"
fi

if [ -d "/data/dsa110-contimg/products" ]; then
    echo "   :check: /data/dsa110-contimg/products exists"
else
    echo "   :cross: /data/dsa110-contimg/products missing"
fi
echo ""

echo "=== Test Complete ==="
