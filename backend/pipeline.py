import json
import os
import glob
from datetime import datetime
from backend.database import get_perfil_activo, create_aplicacion
from backend.filtros.keywords import filtrar_vacante
from backend.filtros.llm_filter import filtrar_con_llm

RAW_DATA_PATH = os.getenv("RAW_DATA_PATH", "./raw_data")
FILTRADAS_PATH = os.getenv("FILTRADAS_PATH", "./filtradas/filtradas.json")


def filtrar_raw_data() -> dict:
    """
    Etapa 1: lee todos los JSONs en raw_data/ (generados por la extensión Chrome),
    aplica el filtro de keywords y sobrescribe filtradas.json con las que pasan,
    rankeadas por score. No llama al LLM.
    """
    perfil = get_perfil_activo()
    if not perfil:
        return {"error": "No hay perfil activo. Activa un perfil antes de filtrar."}

    pattern = os.path.join(RAW_DATA_PATH, "*.json")
    archivos = glob.glob(pattern)

    if not archivos:
        return {"error": f"No hay archivos JSON en {RAW_DATA_PATH}"}

    vacantes = []
    for archivo in archivos:
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                data = json.load(f)
            vacantes.extend(data if isinstance(data, list) else data.get("vacantes", []))
        except Exception as e:
            print(f"Error leyendo {archivo}: {e}")

    stats = {"total": len(vacantes)}
    filtradas = []

    for vacante in vacantes:
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
            "fuente": "linkedin_extension",
            "score": resultado["score"],
            "detalle": resultado["detalle"],
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


def analizar_con_llm() -> dict:
    """
    Etapa 2: lee filtradas.json (salida de filtrar_raw_data) y corre el filtro
    semántico del LLM configurado, guardando en la DB las que pasen.
    """
    perfil = get_perfil_activo()
    if not perfil:
        return {"error": "No hay perfil activo."}

    if not os.path.exists(FILTRADAS_PATH):
        return {"error": f"No hay vacantes filtradas en {FILTRADAS_PATH}. Corre el filtro primero."}

    with open(FILTRADAS_PATH, "r", encoding="utf-8") as f:
        filtradas = json.load(f)

    if not filtradas:
        return {"error": "El archivo de filtradas está vacío."}

    stats = {
        "total": len(filtradas),
        "llm_rechazado": 0,
        "guardadas": 0,
        "duplicadas": 0,
        "perfil": perfil["nombre"],
        "timestamp": datetime.now().isoformat(),
    }

    for vacante in filtradas:
        llm_result = filtrar_con_llm(vacante, perfil)

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
