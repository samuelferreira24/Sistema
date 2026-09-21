#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${SISTEMA_CONTINUIDADE_DIR:-$HOME/.sistema-absoluto/continuidade}"
SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/30_continuidade/continuity.py"
python3 "$SCRIPT" --root "$ROOT" init
python3 "$SCRIPT" --root "$ROOT" verify
echo "Continuidade operacional inicializada em: $ROOT"
