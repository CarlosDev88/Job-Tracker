# Plan de cierre de Job Tracker V1

> Plan ejecutable para convertir el estado actual del proyecto en una V1 pequeña, verificable y terminada. Conserva el guardado y tracking de vacantes. No incluye la implementación de las tareas.

## 1. Objetivo de la V1

Job Tracker V1 debe:

1. Ejecutarse completamente con Docker Compose.
2. Montar una carpeta local donde otros scrapers depositan JSON.
3. Leer, validar, normalizar, deduplicar y puntuar las vacantes.
4. Mostrar resultados ordenados en un Dashboard React.
5. Conservar título, empresa, ubicación, descripción completa, enlace, imágenes y contactos disponibles.
6. Permitir guardar una vacante interesante sin afirmar que ya se aplicó.
7. Permitir guardar una vacante marcándola directamente como aplicada.
8. Permitir hacer seguimiento mediante estado, fecha de aplicación y notas.
9. Persistir el tracking en SQLite al reiniciar los contenedores.
10. No mostrar botones ni exponer integraciones incompletas.

La V1 termina aquí. Generación de CV con IA, análisis LLM, scrapers integrados, autenticación, sincronización externa y analítica avanzada quedan fuera de alcance.

## 2. Decisiones cerradas

### 2.1 Se conserva

- Volumen Docker para la carpeta local de JSON.
- Fuentes actuales: LinkedIn búsqueda, LinkedIn publicaciones, LinkedIn feed y GetOnBord.
- Normalización de los distintos formatos.
- Filtro por keywords, stack, ubicación, experiencia e inglés.
- Filtro especializado para posts del feed.
- Ranking y descripción completa.
- Imágenes, emails y enlaces encontrados en el feed.
- SQLite.
- Guardado de vacantes.
- Tracking mediante estados, fechas y notas.
- Filtros por estado y fuente.
- Un perfil activo editable.

### 2.2 Se elimina

- Segunda etapa de análisis con LLM.
- Conectores Gemini, Claude y ChatGPT.
- Endpoint POST /pipeline/analizar.
- Botón Hacer CV con IA.
- Opciones CLI relacionadas con el LLM.
- SDK y variables de entorno de proveedores LLM.
- Dependencias frontend sin imports reales.
- Archivo vacío frontend/src/Main.jsx.
- Documentación de la extensión Chrome que ya no existe.

### 2.3 Pantallas definitivas

#### Dashboard

- Botón Procesar JSON.
- Resumen de la última ejecución.
- Sección Vacantes estructuradas, ordenada por score 0–100.
- Sección Publicaciones del feed, ordenada por decisión y score interno.
- Tarjetas con score o decisión, fuente, título, empresa y descripción resumida.
- Detalle con descripción completa, ubicación, breakdown, imágenes, emails y enlaces.
- Acción Guardar: crea tracking con estado interno pendiente y etiqueta visible Guardada.
- Acción Guardar como aplicada: crea tracking con estado aplicado y registra fecha_aplicacion.
- Acción Ir a la vacante: solo aparece si existe un enlace válido.
- Acción Copiar empleo: se conserva.
- Si una vacante ya está guardada, muestra su estado y no permite duplicarla.

#### Ofertas

- Lista de vacantes guardadas y aplicadas.
- Filtros por estado y fuente.
- Cambio de estado.
- Notas.
- Fecha de guardado y fecha de aplicación.
- Enlace y descripción completa.
- Eliminación con confirmación.

#### Perfil / Configuración

- Solo se expone un perfil activo.
- Permite editar nombre, keywords a incluir, keywords a excluir, texto de experiencia y ubicación base.
- Se elimina de la UI la creación y activación de varios perfiles.
- linkedin_search_string y getonbord_tags se eliminan si ningún proceso del repositorio los consume.
- La tabla perfiles puede conservarse inicialmente para evitar una migración destructiva.

## 3. Flujo definitivo

~~~text
Carpeta local de descargas
        |
        | volumen Docker
        v
/app/raw_data/*.json
        |
        v
validar -> detectar fuente -> normalizar -> generar dedupe_key
        |
        +-- vacante estructurada -> filtro keywords -> score 0-100
        |
        +-- post de feed -> filtro de dos señales -> REVISAR/TAL_VEZ
        |
        v
deduplicar -> ordenar cada grupo -> escritura atómica de filtradas.json
        |
        v
Dashboard React
        |
        +-- Guardar --------------> SQLite, estado pendiente
        |
        +-- Guardar como aplicada -> SQLite, estado aplicado + fecha
                                           |
                                           v
                                  pantalla de seguimiento
~~~

## 4. Modelo de tracking

### 4.1 Estados

| Valor interno | Etiqueta visible | Uso |
|---|---|---|
| pendiente | Guardada | Interesa, pero todavía no se ha aplicado. |
| aplicado | Aplicada | La aplicación ya fue enviada. |
| cv_enviado | CV enviado | Se envió el CV por un canal adicional. |
| hr_contacto | Contacto RR. HH. | Hubo contacto inicial. |
| prueba_tecnica | Prueba técnica | Existe una prueba pendiente o realizada. |
| entrevista_rrhh | Entrevista RR. HH. | Entrevista con reclutamiento. |
| entrevista_tecnica | Entrevista técnica | Entrevista técnica. |
| oferta | Oferta recibida | Se recibió una oferta. |
| rechazado | Rechazada | La candidatura fue rechazada. |
| ghosted | Sin respuesta | No hubo respuesta después del seguimiento. |

No se impondrá una máquina estricta de transiciones. El usuario puede corregir el estado hacia adelante o atrás.

### 4.2 Identidad persistente

Agregar a job_applications mediante migración idempotente:

~~~sql
dedupe_key TEXT UNIQUE
~~~

Reglas:

- link deja de ser la identidad.
- link puede estar vacío para posts del feed con email, imagen o autor.
- dedupe_key es obligatoria para registros nuevos.
- Los registros existentes se migran sin perder estados, notas ni fechas.
- Antes de migrar se crea una copia de seguridad de SQLite.

### 4.3 Contrato normalizado

~~~json
{
  "dedupe_key": "sha256:...",
  "tipo_resultado": "vacante|feed_post",
  "titulo": "...",
  "empresa": "...",
  "ubicacion": "...",
  "descripcion": "...",
  "link": "...",
  "fuente": "...",
  "score": 0,
  "detalle": {},
  "imagenes": [],
  "contactos": {
    "emails": [],
    "links": []
  },
  "tracking": null
}
~~~

Para vacante, score está entre 0 y 100. Para feed_post, score conserva el valor interno y nunca se presenta como porcentaje.

## 5. Pseudocódigo de correcciones algorítmicas

### 5.1 Normalización centralizada

~~~text
FUNCIÓN normalizar_texto(texto):
    SI texto es nulo:
        RETORNAR ""

    texto = Unicode NFKD(texto)
    texto = eliminar_marcas_diacriticas(texto)
    texto = lowercase(texto)
    texto = reemplazar_espacios_repetidos_por_un_espacio(texto)
    RETORNAR trim(texto)
~~~

Los filtros de vacantes y feed deben usar esta misma función.

### 5.2 Enlace canónico y deduplicación

~~~text
FUNCIÓN canonicalizar_link(link):
    SI link está vacío:
        RETORNAR ""

    parsear URL
    eliminar fragmento
    eliminar parámetros de tracking:
        utm_source, utm_medium, utm_campaign, trackingId, refId, trk
    normalizar host a minúsculas
    eliminar slash final

    SI es LinkedIn Jobs y contiene job ID:
        RETORNAR "https://www.linkedin.com/jobs/view/{job_id}"

    RETORNAR URL normalizada


FUNCIÓN generar_dedupe_key(vacante):
    link = canonicalizar_link(vacante.link)

    SI link no está vacío:
        RETORNAR "link:" + SHA256(link)

    identidad = unir(
        normalizar_texto(vacante.fuente),
        normalizar_texto(vacante.titulo),
        normalizar_texto(vacante.empresa),
        primeros_1000_caracteres(normalizar_texto(vacante.descripcion))
    )

    RETORNAR "contenido:" + SHA256(identidad)
~~~

### 5.3 Requisitos duros y deseables

Errores que se deben corregir:

- Los offsets actuales se calculan sobre descripción pero se aplican sobre título + descripción.
- Solo se inspecciona la primera aparición de una tecnología.
- Una aparición deseable puede ocultar una aparición obligatoria posterior.

Regla: el título se evalúa aparte, se clasifican todas las apariciones en la descripción y cualquier aparición dura prevalece.

~~~text
FUNCIÓN construir_zonas(descripcion):
    marcadores = encontrar_todos_los_headers_duros_y_blandos(descripcion)
    ordenar marcadores por posición

    zonas = []
    tipo_actual = DURO
    inicio = 0

    PARA CADA marcador:
        agregar zona(inicio, marcador.posicion, tipo_actual)
        tipo_actual = marcador.tipo
        inicio = marcador.posicion

    agregar zona(inicio, longitud(descripcion), tipo_actual)
    RETORNAR zonas


FUNCIÓN clasificar_tecnologia(titulo, descripcion, patron):
    titulo = normalizar_texto(titulo)
    descripcion = normalizar_texto(descripcion)

    SI patron aparece en titulo:
        RETORNAR DURO

    zonas = construir_zonas(descripcion)
    apariciones = encontrar_todas_las_apariciones(patron, descripcion)

    SI no hay apariciones:
        RETORNAR AUSENTE

    tipos = conjunto vacío
    PARA CADA aparicion:
        tipos.agregar(tipo_de_zona(aparicion.posicion, zonas))

    SI DURO está en tipos:
        RETORNAR DURO

    RETORNAR BLANDO


FUNCIÓN evaluar_vetos_stack(vacante):
    duros = []
    blandos = []

    PARA CADA tecnologia, patron EN VETOS:
        tipo = clasificar_tecnologia(
            vacante.titulo,
            vacante.descripcion,
            patron
        )

        SI tecnologia == angular Y react también aparece:
            CONTINUAR

        SI tipo == DURO:
            duros.agregar(tecnologia)
        SI tipo == BLANDO:
            blandos.agregar(tecnologia)

    RETORNAR duros, blandos
~~~

### 5.4 Evitar doble puntaje por alias

~~~text
CORE_GRUPOS = {
    react: [react, react.js, reactjs],
    next: [next.js, nextjs],
    typescript: [typescript],
    frontend: [frontend, front-end, front end],
    vtex: [vtex]
}


FUNCIÓN conceptos_presentes(texto, grupos):
    encontrados = []

    PARA CADA concepto, aliases EN grupos:
        SI cualquier alias aparece:
            encontrados.agregar(concepto)

    RETORNAR encontrados
~~~

El score se calcula por concepto. Una keyword del perfil que ya corresponde a un CORE puntuado no vuelve a sumar.

~~~text
FUNCIÓN calcular_score_vacante(vacante, perfil):
    titulo = normalizar_texto(vacante.titulo)
    descripcion = normalizar_texto(vacante.descripcion)

    score = 0
    detalle = detalle_vacio()
    puntuados = conjunto vacío

    core_titulo = conceptos_presentes(titulo, CORE_GRUPOS)
    score += MIN(30, 15 * cantidad(core_titulo))
    registrar core_titulo
    puntuados.agregar(core_titulo)

    PARA CADA concepto CORE no puntuado:
        SI aparece en zona DURO:
            score += 8
            registrar concepto
            puntuados.agregar(concepto)

    PARA CADA concepto SECUNDARIO presente:
        score += 3 una sola vez

    PARA CADA concepto BONUS presente:
        score += 5 una sola vez

    PARA CADA keyword_incluir:
        SI no corresponde a algo ya puntuado Y está presente:
            score += 5

    PARA CADA keyword_excluir:
        SI aparece como requisito DURO:
            score -= 30

    aplicar ajuste por años
    aplicar ajuste por remoto LATAM/Colombia
    aplicar reglas de inglés

    score = limitar(score, 0, 100)
    decision = clasificar_por_umbrales(score)

    RETORNAR score, decision, detalle
~~~

### 5.5 Ranking separado

No se mezclan directamente los porcentajes con el score interno del feed.

~~~text
FUNCIÓN ordenar_resultados(resultados):
    vacantes = resultados de tipo vacante
    feed = resultados de tipo feed_post

    ordenar vacantes por:
        score descendente,
        titulo ascendente,
        empresa ascendente

    prioridad_feed = {
        REVISAR: 2,
        TAL_VEZ: 1
    }

    ordenar feed por:
        prioridad_feed descendente,
        score interno descendente,
        titulo ascendente

    RETORNAR {
        vacantes: vacantes,
        feed: feed
    }
~~~

### 5.6 Pipeline robusto

~~~text
FUNCIÓN filtrar_raw_data():
    perfil = obtener_perfil_activo()

    SI no existe:
        RETORNAR error HTTP y no tocar filtradas.json

    archivos = listar JSON ordenados por nombre

    SI no hay archivos:
        RETORNAR error y conservar resultado anterior

    resultados_por_clave = mapa vacío
    errores = []
    archivos_validos = 0

    PARA CADA archivo:
        INTENTAR:
            contenido = parsear JSON
            items = aceptar lista o objeto con propiedad vacantes
            archivos_validos += 1
        CAPTURAR error:
            errores.agregar(archivo, mensaje)
            CONTINUAR

        fuente = detectar_fuente(archivo)

        PARA CADA item:
            vacante = normalizar_vacante(item, fuente)

            SI vacante es nula O descripción está vacía:
                registrar descarte
                CONTINUAR

            vacante.link = canonicalizar_link(vacante.link)
            vacante.dedupe_key = generar_dedupe_key(vacante)

            SI la clave ya existe:
                conservar el registro con descripción, link e imágenes más completos
                CONTINUAR

            resultado = aplicar_filtro_correspondiente(vacante, perfil)

            SI resultado pasa:
                resultados_por_clave[dedupe_key] = combinar(vacante, resultado)

    SI archivos_validos == 0:
        RETORNAR error con detalle y conservar resultado anterior

    grupos = ordenar_resultados(valores(resultados_por_clave))
    salida = construir_documento_versionado(grupos, stats, errores)

    escribir salida en filtradas.json.tmp
    forzar cierre del archivo
    reemplazar filtradas.json con el temporal

    RETORNAR stats, sin duplicar el ranking completo
~~~

## 6. Pseudocódigo de guardado y tracking

### 6.1 Guardar desde Dashboard

Un solo endpoint acepta el estado inicial pendiente o aplicado.

~~~text
FUNCIÓN guardar_aplicacion(vacante, estado_inicial):
    validar estado_inicial en [pendiente, aplicado]
    validar dedupe_key

    existente = buscar_por_dedupe_key(dedupe_key)

    SI existe:
        RETORNAR HTTP 409 con id y estado existentes

    fecha_aplicacion = AHORA si estado_inicial == aplicado
    en otro caso = null

    insertar vacante completa,
             estado_inicial,
             fecha_encontrada = AHORA,
             fecha_aplicacion

    RETORNAR HTTP 201 con registro creado
~~~

### 6.2 Anexar tracking al ranking

~~~text
FUNCIÓN anexar_tracking(resultados):
    claves = dedupe_key de todos los resultados
    aplicaciones = consultar todas las claves en una sola query
    mapa = indexar aplicaciones por dedupe_key

    PARA CADA resultado:
        SI resultado.dedupe_key está en mapa:
            resultado.tracking = {
                id,
                estado,
                fecha_aplicacion
            }
        SINO:
            resultado.tracking = null

    RETORNAR resultados
~~~

No se hace una consulta SQL por cada tarjeta.

### 6.3 Actualizar estado

~~~text
FUNCIÓN actualizar_estado(id, nuevo_estado):
    validar nuevo_estado
    aplicacion = buscar(id)

    SI no existe:
        RETORNAR HTTP 404

    SI nuevo_estado está en [aplicado, cv_enviado]
       Y fecha_aplicacion está vacía:
        establecer fecha_aplicacion = AHORA

    actualizar estado
    RETORNAR registro actualizado
~~~

Cambiar posteriormente a otro estado no borra fecha_aplicacion.

## 7. API definitiva

| Método | Ruta | Uso |
|---|---|---|
| GET | /health | Salud del backend. |
| POST | /pipeline/filtrar | Procesar JSON. |
| GET | /pipeline/filtradas | Ranking con tracking. |
| GET | /perfil | Obtener perfil activo. |
| PUT | /perfil | Editar perfil activo. |
| POST | /aplicaciones | Guardar o guardar como aplicada. |
| GET | /aplicaciones | Listar tracking con filtros. |
| GET | /aplicaciones/{id} | Ver detalle. |
| PUT | /aplicaciones/{id}/estado | Cambiar estado. |
| PUT | /aplicaciones/{id}/notas | Editar notas. |
| DELETE | /aplicaciones/{id} | Eliminar con confirmación. |
| GET | /stats | Contadores simples. |

Reglas de API:

- Usar códigos HTTP correctos.
- Responder errores como detail legible.
- Comprobar existencia antes de actualizar.
- No devolver HTTP 200 con una propiedad error.
- Validar strings vacíos y estados.
- No filtrar trazas ni secretos.

## 8. Fases de ejecución

### Fase 0 — Respaldo y baseline

- [ ] Confirmar Git limpio.
- [ ] Respaldar el volumen SQLite con fecha.
- [ ] Respaldar filtradas.json fuera de Git.
- [ ] Registrar conteos actuales: archivos, items, filtradas, duplicados y links vacíos.
- [ ] Crear rama codex/cierre-v1.
- [ ] No incluir datos personales en tests.

Salida: respaldo comprobado y baseline registrado.

### Fase 1 — Pruebas de caracterización

- [ ] Agregar pytest como dependencia de desarrollo.
- [ ] Crear fixtures anonimizados para las cuatro fuentes.
- [ ] Cubrir Unicode, fuente, vacante estructurada y feed.
- [ ] Reproducir los dos bugs de zonas.
- [ ] Cubrir alias, enlace vacío y duplicados entre archivos.

Salida: los bugs conocidos están expresados como tests que fallan por la razón esperada.

### Fase 2 — Identidad y deduplicación

- [ ] Centralizar normalización.
- [ ] Implementar enlace canónico.
- [ ] Implementar dedupe_key.
- [ ] Deduplicar todas las fuentes.
- [ ] Conservar el registro duplicado más completo.
- [ ] Agregar migración idempotente.
- [ ] Migrar tracking existente sin perder datos.

Salida: cero duplicados por dedupe_key y los posts sin link se pueden guardar.

### Fase 3 — Corregir algoritmo

- [ ] Separar título y descripción al clasificar zonas.
- [ ] Evaluar todas las apariciones.
- [ ] Hacer prevalecer cualquier aparición dura.
- [ ] Agrupar aliases por concepto.
- [ ] Evitar doble score CORE/perfil.
- [ ] Corregir C1 para evitar coincidencias sin contexto.
- [ ] Mantener inicialmente los umbrales actuales.
- [ ] Revisar una muestra anonimizada después de pasar tests.

Salida: todos los tests algorítmicos pasan.

### Fase 4 — Pipeline robusto

- [ ] Orden determinista de archivos.
- [ ] Errores visibles por archivo.
- [ ] No sobrescribir si ningún archivo es válido.
- [ ] Escritura atómica.
- [ ] Versionar formato de salida.
- [ ] Separar arrays vacantes y feed.
- [ ] POST devuelve stats; GET devuelve ranking.

Salida: dos ejecuciones iguales producen el mismo orden y un JSON corrupto no destruye el resultado anterior.

### Fase 5 — Guardado y tracking

- [ ] Crear POST /aplicaciones con estado inicial.
- [ ] Detectar duplicado mediante dedupe_key y devolver 409.
- [ ] Anexar tracking al ranking con una query agrupada.
- [ ] Conservar fecha de aplicación.
- [ ] Verificar estados, notas, filtros, detalle y eliminación.
- [ ] Mostrar descripción completa en Ofertas.

Salida: una vacante se guarda, cambia de estado y conserva notas después de reiniciar Docker.

### Fase 6 — Simplificar frontend

- [ ] Separar Vacantes y Feed.
- [ ] Agregar Guardar y Guardar como aplicada.
- [ ] Mostrar estado cuando ya está trackeada.
- [ ] Ocultar Ir a la vacante si no hay link.
- [ ] Eliminar Hacer CV con IA.
- [ ] Simplificar Perfiles a Perfil/Configuración.
- [ ] Eliminar Main.jsx vacío.
- [ ] Eliminar dependencias sin imports.
- [ ] Mostrar carga, vacío, éxito y error.
- [ ] Revisar teclado y accesibilidad del modal.

Salida: todo control visible ejecuta una acción real.

### Fase 7 — Eliminar LLM y limpiar backend

- [ ] Eliminar backend/llm.
- [ ] Eliminar llm_filter.py.
- [ ] Eliminar analizar_con_llm y su endpoint.
- [ ] Simplificar run.py.
- [ ] Mantener solo una orden inequívoca de filtrado.
- [ ] Eliminar variables y paquetes LLM.
- [ ] Buscar referencias residuales.

Salida: backend inicia sin SDK ni API keys de IA.

### Fase 8 — Docker reproducible y local

- [ ] Conservar RAW_DATA_HOST_PATH.
- [ ] Conservar volumen persistente SQLite.
- [ ] Agregar healthcheck backend.
- [ ] Esperar backend saludable desde frontend.
- [ ] Limitar puertos a 127.0.0.1.
- [ ] Preferir frontend multi-stage con Nginx y proxy /api.
- [ ] Fijar versiones y lockfiles.
- [ ] Probar desde un clon sin .venv ni node_modules.

Salida: docker compose up --build funciona desde un clon limpio.

### Fase 9 — Verificación automática

- [ ] Crear verificar.sh.
- [ ] Ejecutar tests Python.
- [ ] Ejecutar build frontend.
- [ ] Validar docker compose config.
- [ ] Levantar stack de prueba.
- [ ] Esperar healthcheck.
- [ ] Ejecutar smoke API.
- [ ] Ejecutar flujo E2E.
- [ ] Detener stack sin borrar el volumen real.

Flujo E2E obligatorio:

~~~text
1. Depositar fixture JSON en carpeta temporal.
2. Levantar Docker usando esa carpeta.
3. Procesar JSON.
4. Verificar ranking y descripción completa.
5. Guardar una vacante.
6. Confirmar estado Guardada.
7. Cambiarla a Aplicada.
8. Agregar nota.
9. Reiniciar contenedores.
10. Confirmar estado, fecha y nota persistentes.
~~~

Salida: verificar.sh termina con código 0.

### Fase 10 — Documentación y release

- [ ] Reescribir README con quick start menor a cinco minutos.
- [ ] Documentar los JSON admitidos.
- [ ] Documentar .env sin secretos.
- [ ] Documentar backup y restauración SQLite.
- [ ] Archivar o eliminar documentación obsoleta.
- [ ] Ejecutar checklist final.
- [ ] Crear tag v1.0.0.

Salida: el proyecto puede usarse siguiendo solo README.

## 9. Matriz mínima de pruebas

### Backend unitario

- Unicode estilizado y tildes.
- Canonicalización de URLs.
- dedupe_key con y sin link.
- Headers duros y blandos.
- Tecnología en título.
- Tecnología primero blanda y después dura.
- Tecnología primero dura y después blanda.
- Alias que no suman doble.
- Angular con y sin React.
- Inglés avanzado y C1 fuera de contexto.
- Ubicación presencial, híbrida y remota.
- Feed con una señal: descartado.
- Feed con dos señales: aceptado.
- Feed con veto: descartado.

### Backend integración

- Lista JSON y objeto con propiedad vacantes.
- Archivo corrupto junto a archivo válido.
- Duplicado entre archivos.
- Escritura atómica.
- Migración de base existente.
- Guardado pendiente.
- Guardado aplicado con fecha.
- Duplicado devuelve 409.
- Notas y estado.
- Persistencia SQLite.

### Frontend

- Build de producción.
- Render de ambos grupos.
- Modal con descripción completa.
- Resultado sin link no muestra acción inválida.
- Guardar actualiza tarjeta.
- Guardar como aplicada confirma la fecha.
- Errores API visibles.
- Ofertas permite filtrar, cambiar estado y guardar notas.

## 10. Definición de terminado

- [ ] Un clon limpio arranca con docker compose up --build.
- [ ] La carpeta local aparece dentro del backend.
- [ ] Las cuatro fuentes tienen fixtures y tests.
- [ ] Requisitos duros/deseables funcionan correctamente.
- [ ] No hay duplicados.
- [ ] No se mezclan escalas incompatibles.
- [ ] La descripción completa se conserva y muestra.
- [ ] Un post sin link puede guardarse mediante dedupe_key.
- [ ] Guardar y Guardar como aplicada son acciones diferentes.
- [ ] Tracking, fecha y notas persisten al reiniciar.
- [ ] Ningún botón es placeholder.
- [ ] No quedan rutas, paquetes ni variables LLM.
- [ ] No se versionan secretos ni datos personales.
- [ ] Tests, build, smoke y E2E pasan.
- [ ] README describe el sistema real.
- [ ] Git queda limpio.

## 11. Orden sugerido de commits

1. test: characterize current filtering behavior
2. fix: add canonical identity and global deduplication
3. fix: classify hard and soft requirements correctly
4. fix: separate structured and feed rankings
5. feat: save ranked jobs with an initial tracking state
6. feat: expose tracking state in dashboard results
7. refactor: simplify profile configuration for v1
8. refactor: remove llm pipeline and unused dependencies
9. chore: make docker stack reproducible and local-only
10. test: add api and end-to-end verification
11. docs: replace obsolete documentation with v1 runbook
12. release: v1.0.0

## 12. Reglas durante la ejecución

- No mezclar corrección algorítmica con rediseño visual en el mismo commit.
- No borrar la base antes de probar la migración sobre una copia.
- No usar JSON personal como fixture público.
- No cambiar umbrales mientras se corrigen bugs; recalibrar después con evidencia.
- No introducir nuevas funcionalidades durante el cierre.
- Registrar ideas nuevas en BACKLOG.md.
- Cada fase termina con tests y Git limpio.
- Todo cambio del contrato de filtradas.json actualiza backend, frontend, fixtures y documentación en la misma fase.

## 13. Backlog posterior a V1

- Generación de CV con IA.
- Análisis semántico con LLM.
- Historial completo de estados.
- Recordatorios automáticos.
- Scrapers dentro del repositorio.
- Autenticación y múltiples usuarios.
- Integraciones externas.
- Métricas avanzadas.
- Despliegue público.
