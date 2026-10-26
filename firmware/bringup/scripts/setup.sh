#!/usr/bin/env bash
set -euo pipefail
BRINGUP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
python3 -m venv "$BRINGUP_DIR/.venv"
"$BRINGUP_DIR/.venv/bin/python" -m pip install "platformio==6.1.18" "urllib3<2"
echo "安装完成。进入工程目录后运行 bash scripts/pio.sh run。"
