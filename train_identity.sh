#!/usr/bin/env bash
# Entry point for an authorized K8s train Pod. Does NOT change deployments or release models.
set -euo pipefail
MODE="${1:-full}"
[[ "$MODE" == smoke || "$MODE" == full || "$MODE" == cpu-check ]] || { echo 'usage: train_identity.sh smoke|full|cpu-check [CPU options]' >&2; exit 2; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -gt 0 ]]; then shift; fi
python3 "$SCRIPT_DIR/run_identity.py" "$MODE" "$@"
