#!/usr/bin/env bash
# Shim to the ops/dev setup script so environment checks can find it.

set -e

SCRIPT_DIR="$(cd "$(dirname -- "$0")" && pwd)"
exec "${SCRIPT_DIR}/ops/dev/setup-dev.sh" "$@"
