import json
import os
from datetime import datetime
from difflib import SequenceMatcher
from glob import glob

from backend.database import get_perfil_activo, get_tracking_por_claves, guardar_resultados
from backend.filtros.intencion import detectar_intencion
from backend.filtros.keywords import filtrar_vacante
from backend.filtros.normalizador import normalizar_vacante
from backend.filtros.texto import (
    canonicalizar_link,
    generar_dedupe_key,
    normalizar_texto,
    normalizar_titulo_dedupe,
    sanear_estructura,
)

UMBRAL_SIMILITUD_REPOST = 0.85

# Fuentes que son "posts" de LinkedIn (no una página de vacante real) y por lo
# tanto pueden ser autopromoción de un candidato o ruido social en vez de una
# oferta. linkedin_extension y getonbrd vienen de listados de empleo reales.
FUENTES_INTENCION_INCIERTA = {"linkedin_publicaciones"}

RAW_DATA_PATH = os.getenv("RAW_DATA_PATH", "./raw_data")
FILTRADAS_PATH = os.getenv("FILTRADAS_PATH", "./filtradas/filtradas.json")
FORMATO_VERSION = 2


def _detectar_fuente(nombre_archivo: str) -> str:
    nombre = os.path.basename(nombre_archivo).lower()
    if nombre.startswith("getonbrd"):
        return "getonbrd"
    if nombre.startswith("linkedin_feed"):
        return "linkedin_feed"
    if nombre.startswith("linkedin_publicaciones"):
        return "linkedin_publicaciones"
    if nombre.startswith("linkedin"):
        return "linkedin_extension"
    return "raw_data"


def _items(contenido: object) -> list:
    if isinstance(contenido, list):
        return contenido
    if isinstance(contenido, dict) and isinstance(contenido.get("vacantes"), list):
        return contenido["vacantes"]
    raise ValueError("El JSON debe ser una lista o un objeto con la propiedad vacantes")


def _calidad(resultado: dict) -> tuple:
    return (
        bool(resultado.get("link")),
        len(resultado.get("imagenes", [])),
        len(resultado.get("descripcion", "")),
        resultado.get("score") or 0,
    )


def _fusionar_reposts(resultados: list[dict]) -> tuple[list[dict], int]:
    """Colapsa vacantes que son el mismo aviso reciclado: mismo REF# distinto
    pero título/empresa/descripción iguales, o descripción reescrita casi igual.
    Solo aplica a 'vacante' (el feed usa otra escala y ya se muestra aparte)."""
    vacantes = [item for item in resultados if item["tipo_resultado"] == "vacante"]
    otros = [item for item in resultados if item["tipo_resultado"] != "vacante"]

    por_empresa: dict[str, list[dict]] = {}
    for item in vacantes:
        por_empresa.setdefault(normalizar_texto(item.get("empresa")), []).append(item)

    sobrevivientes: list[dict] = []
    fusionadas = 0

    for grupo in por_empresa.values():
        # Paso 1: colapso exacto por título (sin REF#) + inicio de descripción.
        exactos: dict[str, dict] = {}
        for item in grupo:
            clave = normalizar_titulo_dedupe(item.get("titulo")) + "|" + normalizar_texto(item.get("descripcion"))[:300]
            actual = exactos.get(clave)
            if actual is None:
                exactos[clave] = item
            else:
                fusionadas += 1
                if _calidad(item) > _calidad(actual):
                    exactos[clave] = item

        # Paso 2: colapso por similitud de descripción entre lo que quedó.
        representantes: list[dict] = []
        for item in exactos.values():
            descripcion = normalizar_texto(item.get("descripcion"))
            indice_match = None
            for indice, candidato in enumerate(representantes):
                similitud = SequenceMatcher(None, descripcion, normalizar_texto(candidato.get("descripcion"))).ratio()
                if similitud >= UMBRAL_SIMILITUD_REPOST:
                    indice_match = indice
                    break
            if indice_match is None:
                representantes.append(item)
            else:
                fusionadas += 1
                if _calidad(item) > _calidad(representantes[indice_match]):
                    representantes[indice_match] = item

        sobrevivientes.extend(representantes)

    return sobrevivientes + otros, fusionadas


def _ordenar(resultados: list[dict]) -> dict:
    vacantes = [resultado for resultado in resultados if resultado["tipo_resultado"] == "vacante"]
    feed = [resultado for resultado in resultados if resultado["tipo_resultado"] == "feed_post"]
    def texto_para_ordenar(valor: object) -> str:
        return valor.lower() if isinstance(valor, str) else ""

    vacantes.sort(key=lambda item: (-(item["score"] if item["score"] is not None else -1), texto_para_ordenar(item.get("titulo")), texto_para_ordenar(item.get("empresa"))))
    prioridad = {"REVISAR": 2, "TAL_VEZ": 1}
    feed.sort(key=lambda item: (-prioridad.get(item["detalle"].get("decision"), 0), -item["score"], texto_para_ordenar(item.get("titulo"))))
    return {"vacantes": vacantes, "feed": feed}


def _escribir_atomico(documento: dict) -> None:
    carpeta = os.path.dirname(FILTRADAS_PATH) or "."
    os.makedirs(carpeta, exist_ok=True)
    temporal = FILTRADAS_PATH + ".tmp"
    with open(temporal, "w", encoding="utf-8") as archivo:
        json.dump(documento, archivo, ensure_ascii=False, indent=2)
        archivo.flush()
        os.fsync(archivo.fileno())
    os.replace(temporal, FILTRADAS_PATH)


def filtrar_raw_data() -> dict:
    perfil = get_perfil_activo()
    if not perfil:
        return {"error": "No hay perfil activo."}

    archivos = sorted(glob(os.path.join(RAW_DATA_PATH, "*.json")))
    if not archivos:
        return {"error": f"No hay archivos JSON en {RAW_DATA_PATH}."}

    candidatos, errores = {}, []
    stats = {"archivos": len(archivos), "archivos_validos": 0, "items": 0, "descartadas": 0, "duplicadas": 0}

    for archivo in archivos:
        try:
            with open(archivo, "r", encoding="utf-8") as descriptor:
                items = _items(json.load(descriptor))
            stats["archivos_validos"] += 1
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errores.append({"archivo": os.path.basename(archivo), "mensaje": str(error)})
            continue

        fuente = _detectar_fuente(archivo)
        for item in items:
            stats["items"] += 1
            if not isinstance(item, dict):
                stats["descartadas"] += 1
                continue
            vacante = normalizar_vacante(item, fuente)
            if not vacante or not vacante.get("descripcion", "").strip():
                stats["descartadas"] += 1
                continue

            vacante = sanear_estructura(vacante)
            vacante["fuente"] = fuente
            vacante["link"] = canonicalizar_link(vacante.get("link"))
            vacante["dedupe_key"] = generar_dedupe_key(vacante)

            if vacante["tipo_resultado"] == "feed_post":
                resultado = {
                    **vacante,
                    "score": vacante["feed_score"],
                    "detalle": {"decision": vacante["feed_decision"]},
                }
            else:
                resultado = None
                if fuente in FUENTES_INTENCION_INCIERTA:
                    intencion = detectar_intencion(vacante.get("titulo", ""), vacante.get("descripcion", ""))
                    if intencion in ("CANDIDATO", "RUIDO_SOCIAL"):
                        # Autopromoción de alguien buscando trabajo, o ruido social
                        # (cumpleaños, aniversarios): no es una oferta, se descarta.
                        stats["descartadas"] += 1
                        continue
                    if intencion == "INDETERMINADO":
                        # Ni una señal clara de oferta ni de candidato/ruido: en vez de
                        # arriesgar un descarte o un puntaje engañoso, se deja sin
                        # puntuar y marcada para revisión manual.
                        resultado = {
                            **vacante,
                            "score": None,
                            "detalle": {
                                "decision": "REVISAR_INTENCION",
                                "positivos": [], "negativos": [],
                                "gaps_duros": [], "gaps_blandos": [],
                            },
                        }
                if resultado is None:
                    filtro = filtrar_vacante(vacante, perfil)
                    if not filtro["pasa"]:
                        stats["descartadas"] += 1
                        continue
                    resultado = {**vacante, "score": filtro["score"], "detalle": filtro["detalle"]}

            existente = candidatos.get(resultado["dedupe_key"])
            if existente:
                stats["duplicadas"] += 1
                if _calidad(resultado) > _calidad(existente):
                    candidatos[resultado["dedupe_key"]] = resultado
            else:
                candidatos[resultado["dedupe_key"]] = resultado

    if stats["archivos_validos"] == 0:
        return {"error": "Ningún JSON pudo leerse.", "errores": errores}

    resultados_fusionados, fusiones_extra = _fusionar_reposts(list(candidatos.values()))
    stats["duplicadas"] += fusiones_extra

    # Histórico: además del archivo filtradas.json (snapshot de la corrida
    # actual), cada resultado se guarda/actualiza en SQLite por dedupe_key
    # para acumular histórico entre corridas sin duplicar filas.
    guardar_resultados(resultados_fusionados)

    grupos = _ordenar(resultados_fusionados)
    stats["filtradas"] = len(resultados_fusionados)
    stats["perfil"] = perfil["nombre"]
    documento = {
        "version": FORMATO_VERSION,
        "generado_en": datetime.now().isoformat(),
        "stats": stats,
        "errores": errores,
        **grupos,
    }
    _escribir_atomico(documento)
    return {"ok": True, "stats": stats, "errores": errores}


def leer_filtradas() -> dict:
    if not os.path.exists(FILTRADAS_PATH):
        return {"version": FORMATO_VERSION, "vacantes": [], "feed": [], "stats": {}, "errores": []}
    with open(FILTRADAS_PATH, "r", encoding="utf-8") as archivo:
        contenido = json.load(archivo)

    if isinstance(contenido, list):
        contenido = {
            "version": 1,
            "vacantes": [item for item in contenido if not item.get("revisar_manual")],
            "feed": [item for item in contenido if item.get("revisar_manual")],
            "stats": {},
            "errores": [],
        }

    resultados = contenido.get("vacantes", []) + contenido.get("feed", [])
    tracking = get_tracking_por_claves([resultado.get("dedupe_key") for resultado in resultados])
    for resultado in resultados:
        resultado["tracking"] = tracking.get(resultado.get("dedupe_key"))
    return contenido
