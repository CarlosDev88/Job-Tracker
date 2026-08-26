#!/usr/bin/env bash
# Respaldo y restauración de la base de datos.
#
# Lo que protege: el seguimiento de tus postulaciones (a qué aplicaste, cuándo,
# en qué estado va y tus notas) y la configuración del perfil. Las vacantes se
# pueden volver a scrapear; eso no.
#
# La base vive en el volumen Docker 'db_data'. Sobrevive a 'docker compose down',
# pero NO a 'docker compose down -v': ese comando la borra sin preguntar.
#
#   ./respaldo.sh                     crea un respaldo con fecha en respaldos/
#   ./respaldo.sh restaurar <archivo> restaura ese respaldo
#   ./respaldo.sh listar              muestra los respaldos existentes

set -euo pipefail

CARPETA="respaldos"
RUTA_EN_CONTENEDOR="/app/data/job_tracker.db"

servicio_activo() {
    [ -n "$(docker compose ps -q backend 2>/dev/null)" ]
}

case "${1:-crear}" in
crear)
    if ! servicio_activo; then
        echo "El backend no está corriendo. Arráncalo con: docker compose up -d" >&2
        exit 1
    fi
    mkdir -p "$CARPETA"
    destino="$CARPETA/job_tracker_$(date +%Y%m%d_%H%M%S).db"

    # Se usa la API de respaldo de SQLite en vez de copiar el archivo: con WAL
    # activo, copiar el .db suelto puede dejar fuera transacciones que todavía
    # están en el journal y producir un respaldo corrupto o incompleto.
    docker compose exec -T backend python -c "
import sqlite3
origen = sqlite3.connect('$RUTA_EN_CONTENEDOR')
copia = sqlite3.connect('/tmp/respaldo.db')
with copia:
    origen.backup(copia)
copia.close(); origen.close()
"
    docker compose cp "backend:/tmp/respaldo.db" "$destino"
    docker compose exec -T backend rm -f /tmp/respaldo.db

    echo "Respaldo creado: $destino ($(du -h "$destino" | cut -f1))"
    ;;

restaurar)
    archivo="${2:-}"
    if [ -z "$archivo" ]; then
        echo "Falta el archivo. Uso: ./respaldo.sh restaurar respaldos/job_tracker_AAAAMMDD_HHMMSS.db" >&2
        exit 1
    fi
    if [ ! -f "$archivo" ]; then
        echo "No existe el archivo: $archivo" >&2
        exit 1
    fi
    if ! servicio_activo; then
        echo "El backend no está corriendo. Arráncalo con: docker compose up -d" >&2
        exit 1
    fi

    echo "Esto reemplaza la base actual con '$archivo'."
    printf "Se perderá el seguimiento posterior a ese respaldo. ¿Continuar? [s/N] "
    read -r respuesta
    [ "$respuesta" = "s" ] || [ "$respuesta" = "S" ] || { echo "Cancelado."; exit 0; }

    # Antes de pisar nada, se guarda la base actual: si el respaldo estaba
    # corrupto, todavía hay a dónde volver.
    if [ -n "$(docker compose ps -q backend)" ]; then
        mkdir -p "$CARPETA"
        previo="$CARPETA/antes_de_restaurar_$(date +%Y%m%d_%H%M%S).db"
        docker compose cp "backend:$RUTA_EN_CONTENEDOR" "$previo" 2>/dev/null \
            && echo "Base actual guardada en: $previo"
    fi

    docker compose cp "$archivo" "backend:$RUTA_EN_CONTENEDOR"
    # Los archivos -wal y -shm que queden son de la base vieja y la
    # contradicen: hay que quitarlos para que SQLite lea la restaurada.
    docker compose exec -T backend sh -c "rm -f ${RUTA_EN_CONTENEDOR}-wal ${RUTA_EN_CONTENEDOR}-shm"
    docker compose restart backend >/dev/null

    echo "Restaurado. El backend se reinició."
    ;;

listar)
    if [ ! -d "$CARPETA" ] || [ -z "$(ls -A "$CARPETA" 2>/dev/null)" ]; then
        echo "No hay respaldos todavía. Crea uno con: ./respaldo.sh"
        exit 0
    fi
    ls -lh "$CARPETA"/*.db
    ;;

*)
    echo "Uso: ./respaldo.sh [crear|restaurar <archivo>|listar]" >&2
    exit 1
    ;;
esac
