#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

docker compose config --quiet
docker compose up --build -d
for intento in $(seq 1 30); do
    if curl -fsS http://localhost:8000/health >/dev/null; then
        break
    fi
    sleep 2
done
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:5173/ >/dev/null
echo "Verificación de Docker y salud completada."
