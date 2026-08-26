# Job Tracker V1

Herramienta local para procesar JSON de vacantes, puntuarlas contra un perfil y hacer seguimiento de las oportunidades guardadas.

## Qué hace

- Lee JSON desde una carpeta local montada en Docker.
- Normaliza y deduplica vacantes de LinkedIn y GetOnBord.
- Puntúa vacantes estructuradas y clasifica posts del feed por separado.
- Conserva la descripción completa.
- Permite guardar una vacante o guardarla directamente como aplicada.
- Persiste estados, fechas y notas en SQLite.

## Requisito previo: carpeta de datos del scraper

El pipeline **no descarga nada por si mismo**: lee los JSON que el scraper deja en una
carpeta de tu equipo. Por convencion esa carpeta es `Downloads/JobTracker`
(en Windows la carpeta se muestra como "Descargas" pero en disco se llama `Downloads`).

1. Crea la carpeta si no existe:

| Sistema | Ruta a crear |
| --- | --- |
| Windows | `C:\Users\TU_USUARIO\Downloads\JobTracker` |
| WSL | `/mnt/c/Users/TU_USUARIO/Downloads/JobTracker` |
| macOS | `/Users/TU_USUARIO/Downloads/JobTracker` |
| Linux | `/home/TU_USUARIO/Downloads/JobTracker` |

2. Coloca ahi los archivos `.json` que descarga el scraper. Se montan dentro del
   contenedor en `/app/raw_data` en modo solo lectura, asi que el proyecto nunca
   modifica ni borra tus descargas.

## Inicio rapido

1. Copia el archivo de configuracion:

~~~bash
cp .env.example .env
~~~

En PowerShell: `Copy-Item .env.example .env`

2. Edita `RAW_DATA_HOST_PATH` en `.env` con la ruta de tu carpeta segun tu sistema
   operativo. **Es el unico valor que cambia entre sistemas.**

~~~ini
# Windows (Docker Desktop) - usa barras normales "/", Docker las traduce
RAW_DATA_HOST_PATH=C:/Users/TU_USUARIO/Downloads/JobTracker

# WSL (Docker dentro de WSL)
RAW_DATA_HOST_PATH=/mnt/c/Users/TU_USUARIO/Downloads/JobTracker

# macOS
RAW_DATA_HOST_PATH=/Users/TU_USUARIO/Downloads/JobTracker

# Linux
RAW_DATA_HOST_PATH=/home/TU_USUARIO/Downloads/JobTracker
~~~

Si dejas el valor por defecto (`./raw_data`), el pipeline leera la carpeta
`raw_data/` del propio repositorio.

> Ojo al migrar de WSL a Windows nativo: la ruta `/mnt/c/...` **solo funciona en WSL**.
> En Windows con Docker Desktop debe ser `C:/Users/...` o el volumen se monta vacio y
> veras el error "No hay archivos JSON en /app/raw_data".

3. Enciende Docker Desktop y ejecuta:

~~~bash
docker compose up --build
~~~

4. Abre http://localhost:5173 y pulsa Procesar JSON.

La API de salud queda disponible en http://localhost:8000/health.

## Flujo de uso

1. Un scraper externo deja JSON en `Downloads/JobTracker` (la carpeta configurada en `RAW_DATA_HOST_PATH`).
2. Dashboard procesa y muestra el ranking.
3. Usa Guardar para seguir una vacante sin haber aplicado.
4. Usa Guardar como aplicada si ya enviaste la aplicación.
5. Gestiona estado y notas en Seguimiento de vacantes.

## Formato mínimo de vacante estructurada

~~~json
{
  "titulo": "Senior Frontend Engineer",
  "empresa": "Acme",
  "ubicacion": "Colombia remoto",
  "descripcion": "Requisitos: React y TypeScript...",
  "link": "https://www.linkedin.com/jobs/view/123"
}
~~~

Los archivos pueden ser una lista de vacantes o un objeto con la propiedad vacantes. El feed de LinkedIn admite su formato actual con tarjeta_empleo o descripción libre.

## Datos y respaldo

SQLite vive en el volumen Docker db_data. Antes de cambios importantes, crea un respaldo:

~~~bash
docker compose cp backend:/app/data/job_tracker.db ./backup-job-tracker.db
~~~

No versionar .env, raw_data ni filtradas.json.

## Verificación

Cuando Docker esté encendido:

~~~bash
./verificar.sh
~~~

Los scripts `.sh` requieren un shell tipo bash. En Windows usa **Git Bash** o **WSL**;
desde PowerShell corre los comandos equivalentes de `docker compose` a mano.
