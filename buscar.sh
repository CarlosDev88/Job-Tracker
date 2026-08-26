#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Entorno virtual no encontrado."
    echo "Crea uno con: python -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt"
    exit 1
fi

source .venv/bin/activate
python backend/run.py --filtrar
