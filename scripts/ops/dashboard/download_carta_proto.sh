#!/bin/bash
# Download CARTA Protocol Buffer definitions
#
# This script downloads the latest CARTA .proto files from the official repository
# and places them in the frontend/public directory for use by the CARTA client.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
PUBLIC_DIR="$FRONTEND_DIR/public"
PROTO_DIR="$PUBLIC_DIR/proto"

# Create proto directory if it doesn't exist
mkdir -p "$PROTO_DIR"

# CARTA protobuf repository
CARTA_PROTO_REPO="https://github.com/CARTAvis/carta-protobuf"
CARTA_PROTO_URL="https://raw.githubusercontent.com/CARTAvis/carta-protobuf/main"

# List of proto files to download (update based on actual CARTA structure)
PROTO_FILES=(
  "carta.proto"
)

echo "Downloading CARTA Protocol Buffer definitions..."
echo "Repository: $CARTA_PROTO_REPO"
echo "Output directory: $PROTO_DIR"
echo ""

# Download each proto file
for proto_file in "${PROTO_FILES[@]}"; do
  echo "Downloading $proto_file..."
  output_file="$PROTO_DIR/$proto_file"
  
  if curl -f -s -o "$output_file" "$CARTA_PROTO_URL/$proto_file"; then
    echo "  :check: Downloaded $proto_file ($(wc -c < "$output_file" | tr -d ' ') bytes)"
  else
    echo "  :cross: Failed to download $proto_file"
    exit 1
  fi
done

echo ""
echo "Successfully downloaded CARTA Protocol Buffer definitions!"
echo "Files are available at: $PROTO_DIR"
echo ""
echo "To use these files, update cartaClient.ts:"
echo "  const root = await protobuf.load('$PROTO_DIR/carta.proto');"

