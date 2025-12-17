#!/usr/bin/env bash
# Install a Raspberry Pi desktop launcher for the HX711 GUI.
# Creates ~/.local/share/applications/hx711-loadcell-gui.desktop

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DESKTOP_DIR="${HOME}/.local/share/applications"
DESKTOP_FILE="${DESKTOP_DIR}/hx711-loadcell-gui.desktop"

mkdir -p "${DESKTOP_DIR}"

cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=HX711 Load Cell GUI
Comment=Start the HX711 load cell GUI
Exec=env PYTHONUNBUFFERED=1 bash -lc 'cd "${REPO_DIR}" && python3 main.py'
Path=${REPO_DIR}
Terminal=false
Categories=Utility;Science;
EOF

chmod 644 "${DESKTOP_FILE}"
echo "Desktop launcher created at ${DESKTOP_FILE}"

