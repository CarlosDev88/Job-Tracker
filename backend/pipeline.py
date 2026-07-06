import json
import os
import glob
from datetime import datetime
from backend.database import get_perfil_activo, create_aplicacion, update_estado
from backend.filtros.keywords import filtrar_vacante
from backend.filtros.llm_filter import filtrar_con_llm
from backend.filtros.normalizador import normalizar_vacante
from backend.filtros.feed_filter import normalizar as normalizar_texto_feed

RAW_DATA_PATH = os.getenv("RAW_DATA_PATH", "./raw_data")
FILTRADAS_PATH = os.getenv("FILTRADAS_PATH", "./filtradas/filtradas.json")


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


def filtrar_raw_data() -> dict:
    """
    Etapa 1: lee todos los JSONs en raw_data/ (generados por la extensión Chrome),
    aplica el filtro de keywords y sobrescribe filtradas.json con las que pasan,
    rankeadas por score. No llama al LLM en ningún punto. Los posts del feed de
    LinkedIn sin tarjeta_empleo estructurada no pasan por el filtro genérico de
    keywords.py: usan el filtro dedicado de feed_filter.py (ver
    algoritmo_feed.md), pensado específicamente para captions cortos — su
    propia decisión (REVISAR/TAL_VEZ) y score se usan tal cual.
    """
    perfil = get_perfil_activo()
    if not perfil:
        return {"error": "No hay perfil activo. Activa un perfil antes de filtrar."}

    pattern = os.path.join(RAW_DATA_PATH, "*.json")
    archivos = glob.glob(pattern)

    if not archivos:
        return {"error": f"No hay archivos JSON en {RAW_DATA_PATH}"}

    vacantes = []
    vistos_feed = set()
    for archivo in archivos:
        fuente = _detectar_fuente(archivo)
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else data.get("vacantes", [])
            for item in items:
                # Un mismo post de feed suele aparecer repetido entre scrapes distintos.
                if fuente == "linkedin_feed" and not (item.get("tiene_tarjeta_empleo") and item.get("tarjeta_empleo")):
                    clave = normalizar_texto_feed(item.get("descripcion") or "")[:200]
                    if clave in vistos_feed:
                        continue
                    vistos_feed.add(clave)

                vacante = normalizar_vacante(item, fuente)
                if vacante is not None:
                    vacante["fuente"] = fuente
                    vacantes.append(vacante)
        except Exception as e:
            print(f"Error leyendo {archivo}: {e}")

    stats = {"total": len(vacantes)}
    filtradas = []

    for vacante in vacantes:
        if "feed_decision" in vacante:
            filtradas.append({
                "titulo": vacante.get("titulo", ""),
                "empresa": vacante.get("empresa", ""),
                "ubicacion": vacante.get("ubicacion", ""),
                "descripcion": vacante.get("descripcion", ""),
                "link": vacante.get("link", ""),
                "fuente": vacante.get("fuente", ""),
                "score": vacante["feed_score"],
                "detalle": {
                    "decision": vacante["feed_decision"],
                    "emails": vacante.get("feed_emails", []),
                    "links": vacante.get("feed_links", []),
                },
                "revisar_manual": True,
                "imagenes": vacante.get("imagenes", []),
            })
            continue

        resultado = filtrar_vacante(vacante, perfil)

        if not resultado["pasa"]:
            stats[resultado["razon"]] = stats.get(resultado["razon"], 0) + 1
            continue

        filtradas.append({
            "titulo": vacante.get("titulo", ""),
            "empresa": vacante.get("empresa", ""),
            "ubicacion": vacante.get("ubicacion", ""),
            "descripcion": vacante.get("descripcion", ""),
            "link": vacante.get("link", ""),
            "fuente": vacante.get("fuente", ""),
            "score": resultado["score"],
            "detalle": resultado["detalle"],
            "revisar_manual": False,
            "imagenes": vacante.get("imagenes", []),
        })

    filtradas.sort(key=lambda v: v["score"], reverse=True)

    os.makedirs(os.path.dirname(FILTRADAS_PATH), exist_ok=True)
    with open(FILTRADAS_PATH, "w", encoding="utf-8") as f:
        json.dump(filtradas, f, ensure_ascii=False, indent=2)

    stats["filtradas"] = len(filtradas)
    stats["perfil"] = perfil["nombre"]
    stats["timestamp"] = datetime.now().isoformat()
    stats["ranking"] = filtradas
    return stats


def leer_filtradas() -> list:
    """Lee filtradas.json tal cual quedó de la última corrida de filtrar_raw_data."""
    if not os.path.exists(FILTRADAS_PATH):
        return []
    with open(FILTRADAS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def convertir_a_oferta(vacante: dict) -> dict:
    """
    Convierte una vacante prefiltrada (fila de filtradas.json) directo en una
    oferta con estado 'aplicado', sin pasar por el LLM — reemplaza al viejo
    flujo de "Analizar con IA": ahora el usuario decide manualmente cuál
    vacante aplicar, en vez de que el LLM decida por él.
    """
    perfil = get_perfil_activo()
    if not perfil:
        return {"error": "No hay perfil activo."}

    creada = create_aplicacion({
        "perfil_id": perfil["id"],
        "titulo": vacante.get("titulo", ""),
        "empresa": vacante.get("empresa", ""),
        "ubicacion": vacante.get("ubicacion", ""),
        "descripcion": vacante.get("descripcion", ""),
        "link": vacante.get("link", ""),
        "fuente": vacante.get("fuente", ""),
        "score": vacante.get("score", 0),
        "score_detalle": vacante.get("detalle", {}),
    })

    if creada is None:
        return {"error": "Esta vacante ya estaba guardada (link duplicado)."}

    return update_estado(creada["id"], "aplicado")


def analizar_con_llm(links: list[str] | None = None) -> dict:
    """
    Etapa 2: lee filtradas.json (salida de filtrar_raw_data) y corre el filtro
    semántico del LLM configurado, guardando en la DB las que pasen.

    `links` permite analizar solo un subconjunto elegido a mano — la capa
    gratuita del LLM da ~20 llamadas al día, así que en vez de gastarlas todas
    en el ranking completo, el usuario puede filtrar manualmente cuáles vale
    la pena mandar al LLM.
    """
    perfil = get_perfil_activo()
    if not perfil:
        return {"error": "No hay perfil activo."}

    if not os.path.exists(FILTRADAS_PATH):
        return {"error": f"No hay vacantes filtradas en {FILTRADAS_PATH}. Corre el filtro primero."}

    with open(FILTRADAS_PATH, "r", encoding="utf-8") as f:
        filtradas = json.load(f)

    if links is not None:
        links_set = set(links)
        filtradas = [v for v in filtradas if v.get("link") in links_set]

    if not filtradas:
        return {"error": "No hay vacantes para analizar."}

    stats = {
        "total": len(filtradas),
        "llm_rechazado": 0,
        "guardadas": 0,
        "duplicadas": 0,
        "errores": 0,
        "cuota_agotada": False,
        "perfil": perfil["nombre"],
        "timestamp": datetime.now().isoformat(),
    }

    for i, vacante in enumerate(filtradas):
        llm_result = filtrar_con_llm(vacante, perfil)

        if llm_result.get("cuota_agotada"):
            stats["cuota_agotada"] = True
            stats["pendientes"] = len(filtradas) - i
            break

        if llm_result.get("error"):
            stats["errores"] += 1
            continue

        if not llm_result["pasa"]:
            stats["llm_rechazado"] += 1
            continue

        saved = create_aplicacion({
            "perfil_id": perfil["id"],
            "titulo": vacante.get("titulo", ""),
            "empresa": vacante.get("empresa", ""),
            "ubicacion": vacante.get("ubicacion", ""),
            "descripcion": vacante.get("descripcion", ""),
            "link": vacante.get("link", ""),
            "fuente": vacante.get("fuente", ""),
            "score": vacante.get("score", 0),
            "score_detalle": vacante.get("detalle", {}),
            "llm_razon": llm_result["razon"],
        })

        if saved:
            stats["guardadas"] += 1
        else:
            stats["duplicadas"] += 1

    return stats
