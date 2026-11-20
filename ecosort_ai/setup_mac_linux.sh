#!/usr/bin/env bash
# Instalación en macOS/Linux: crea el entorno virtual e instala dependencias.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo
echo "Listo. En VS Code: Cmd/Ctrl+Shift+P > 'Python: Select Interpreter' > venv/bin/python"
echo "Luego prueba:  python -m pytest -v test_detector.py"
