#!/bin/bash
# Job Tracker — Script de ejecución
# Uso:
#   ./buscar.sh --perfil "Frontend React Senior"
#   ./buscar.sh --importar
#   ./buscar.sh --listar-perfiles

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "❌ Entorno virtual no encontrado. Ejecuta:"
    echo "   python -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt"
    exit 1
fi

source .venv/bin/activate
python backend/run.py "$@"