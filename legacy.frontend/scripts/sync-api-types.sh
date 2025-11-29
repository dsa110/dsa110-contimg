#!/usr/bin/env bash
#
# Generate TypeScript types from backend OpenAPI schema
# This ensures frontend types stay in sync with backend API
#
# Usage: ./scripts/sync-api-types.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="/data/dsa110-contimg/backend"
OUTPUT_DIR="$FRONTEND_DIR/src/api/generated"

echo ":anticlockwise_downwards_and_upwards_open_circle_arrows: Syncing API types from backend OpenAPI schema..."

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Generate OpenAPI schema from backend
echo ":memo: Extracting OpenAPI schema from backend..."
cd "$BACKEND_DIR"

# Use Python to extract and save OpenAPI schema
python3 << 'EOF'
import json
import sys
sys.path.insert(0, 'src')

try:
    from dsa110_contimg.api import app
    schema = app.openapi()
    
    # Write to file
    output_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/openapi.json'
    with open(output_path, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f":white_heavy_check_mark: OpenAPI schema written to {output_path}")
    
    # Print summary
    paths = len(schema.get('paths', {}))
    schemas = len(schema.get('components', {}).get('schemas', {}))
    print(f"   {paths} endpoints, {schemas} schemas")
    
except Exception as e:
    print(f":cross_mark: Failed to extract OpenAPI schema: {e}")
    sys.exit(1)
EOF "$OUTPUT_DIR/openapi.json"

# Check if openapi-typescript is available
cd "$FRONTEND_DIR"

if ! command -v npx &> /dev/null; then
    echo ":cross_mark: npx not found. Please install Node.js."
    exit 1
fi

# Generate TypeScript types using openapi-typescript
echo ":wrench: Generating TypeScript types..."
if npx openapi-typescript "$OUTPUT_DIR/openapi.json" -o "$OUTPUT_DIR/api-types.ts" 2>/dev/null; then
    echo ":white_heavy_check_mark: TypeScript types generated at $OUTPUT_DIR/api-types.ts"
else
    echo ":warning_sign::variation_selector-16:  openapi-typescript not installed. Install with: npm install -D openapi-typescript"
    echo "   Skipping TypeScript generation, but OpenAPI schema saved."
fi

# Generate a diff report comparing manual types to generated types
echo ""
echo ":bar_chart: Type comparison report:"
echo "   Manual types:    src/api/types.ts"
echo "   Generated types: src/api/generated/api-types.ts"
echo ""
echo "   To compare: diff -u src/api/types.ts src/api/generated/api-types.ts | head -100"
echo ""
echo ":white_heavy_check_mark: API type sync complete!"
