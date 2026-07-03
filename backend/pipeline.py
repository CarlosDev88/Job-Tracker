import json
import os
import glob
from datetime import datetime
from backend.database import get_perfil_activo, create_aplicacion
from backend.filtros.keywords import filtrar_vacante
from backend.filtros.llm_filter import filtrar_con_llm

RAW_DATA_PATH = os.getenv("RAW_DATA_PATH", "./raw_data")


def procesar_vacantes(vacantes: list, fuente: str) -> dict:
    """
    Corre el pipeline completo sobre una lista de vacantes.
    
    Pipeline:
      Filtro 0: blacklist dura
      Filtro 1: scoring por pesos
      Filtro 2: LLM semántico (solo score >= 50)
      → DB
    
    Retorna stats del procesamiento.
    """
    perfil = get_perfil_activo()
    if not perfil:
        return {"error": "No hay perfil activo. Activa un perfil antes de correr el pipeline."}

    stats = {
        "total": len(vacantes),
        "blacklist": 0,
        "score_bajo": 0,
        "llm_rechazado": 0,
        "guardadas": 0,
        "duplicadas": 0,
        "perfil": perfil["nombre"],
        "timestamp": datetime.now().isoformat(),
    }

    for vacante in vacantes:
        resultado = filtrar_vacante(vacante, perfil)

        if not resultado["pasa"]:
            stats[resultado["razon"]] = stats.get(resultado["razon"], 0) + 1
            print(f"❌ [{resultado["razon"]}] score={resultado["score"]} | {vacante.get("titulo","")[:50]}")
            continue

        print(f"✅ score={resultado["score"]} | {vacante.get("titulo","")[:50]}")
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
            "fuente": fuente,
            "score": resultado["score"],
            "score_detalle": resultado["detalle"],
            "llm_razon": llm_result["razon"],
        })

        if saved:
            stats["guardadas"] += 1
        else:
            stats["duplicadas"] += 1

    return stats


def importar_raw_data() -> dict:
    """
    Lee todos los JSONs en raw_data/ (generados por la extensión Chrome)
    y los pasa por el pipeline.
    """
    pattern = os.path.join(RAW_DATA_PATH, "*.json")
    archivos = glob.glob(pattern)

    if not archivos:
        return {"error": f"No hay archivos JSON en {RAW_DATA_PATH}"}

    total_stats = {
        "archivos_procesados": 0,
        "total": 0,
        "guardadas": 0,
        "duplicadas": 0,
        "rechazadas": 0,
    }

    for archivo in archivos:
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Acepta tanto lista directa como { "vacantes": [...] }
            vacantes = data if isinstance(data, list) else data.get("vacantes", [])
            fuente = "linkedin_extension"

            stats = procesar_vacantes(vacantes, fuente)
            total_stats["archivos_procesados"] += 1
            total_stats["total"] += stats.get("total", 0)
            total_stats["guardadas"] += stats.get("guardadas", 0)
            total_stats["duplicadas"] += stats.get("duplicadas", 0)
            total_stats["rechazadas"] += (
                stats.get("total", 0) - stats.get("guardadas", 0) - stats.get("duplicadas", 0)
            )

        except Exception as e:
            total_stats[f"error_{os.path.basename(archivo)}"] = str(e)

    return total_stats