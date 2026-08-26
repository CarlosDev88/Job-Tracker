# Job Tracker V1

Herramienta local para procesar JSON de vacantes, puntuarlas contra un perfil y hacer seguimiento de las oportunidades guardadas.

## Qué hace

- Lee JSON desde una carpeta local montada en Docker.
- Normaliza y deduplica vacantes de LinkedIn y GetOnBord.
- Puntúa vacantes estructuradas y clasifica posts del feed por separado.
- Conserva la descripción completa.
- Permite guardar una vacante o guardarla directamente como aplicada.
- Persiste estados, fechas y notas en SQLite.

## Inicio rápido

1. Copia el archivo de configuración:

~~~bash
cp .env.example .env
~~~

2. Ajusta RAW_DATA_HOST_PATH en .env para que apunte a la carpeta local que recibe los JSON.

3. Enciende Docker Desktop y ejecuta:

~~~bash
docker compose up --build
~~~

4. Abre http://localhost:5173 y pulsa Procesar JSON.

La API de salud queda disponible en http://localhost:8000/health.

## Flujo de uso

1. Un scraper externo deja JSON en la carpeta configurada.
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
