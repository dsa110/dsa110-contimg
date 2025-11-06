#!/bin/bash
# Convenience script to run CubiCal calibration in Docker

set -e

# Default values
MS_PATH=""
FIELD=""
OUTPUT_DIR="/scratch/calibration_test/cubical"
IMAGE="dsa110-cubical:experimental"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ms)
            MS_PATH="$2"
            shift 2
            ;;
        --field)
            FIELD="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --image)
            IMAGE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --ms <ms_path> --field <field> [--output-dir <dir>] [--image <image>]"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$MS_PATH" ]] || [[ -z "$FIELD" ]]; then
    echo "ERROR: --ms and --field are required"
    echo "Usage: $0 --ms <ms_path> --field <field> [--output-dir <dir>]"
    exit 1
fi

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Run calibration in Docker
echo "Running CubiCal calibration in Docker..."
echo "  MS: $MS_PATH"
echo "  Field: $FIELD"
echo "  Output: $OUTPUT_DIR"
echo "  Image: $IMAGE"
echo

docker run -it --rm \
  --gpus all \
  -v /scratch:/scratch:ro \
  -v /data:/data:ro \
  -v "$OUTPUT_DIR:/workspace/output:rw" \
  -v /data/dsa110-contimg/src/dsa110_contimg/calibration/cubical_experimental:/workspace/cubical_experimental:ro \
  "$IMAGE" \
  bash -c "
    source /opt/conda/etc/profile.d/conda.sh && \
    conda activate cubical && \
    cd /workspace && \
    python -m cubical_experimental.cubical_cli \
      --ms $MS_PATH \
      --field $FIELD \
      --output-dir /workspace/output
  "

echo
echo "Calibration complete. Results saved to: $OUTPUT_DIR"
