#!/usr/bin/env bash
# Entry point for an authorized K8s train Pod. Does NOT change deployments or release models.
set -euo pipefail
MODE="${1:-full}"
[[ "$MODE" == smoke || "$MODE" == full ]] || { echo 'usage: train_identity.sh smoke|full' >&2; exit 2; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/run_identity.py" "$MODE"
