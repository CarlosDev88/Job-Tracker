from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json

from backend.database import (
    init_db,
    get_perfiles,
    get_perfil,
    create_perfil,
    update_perfil,
    activar_perfil,
    get_aplicaciones,
    get_aplicacion,
    update_estado,
    update_notas,
    delete_aplicacion,
    get_stats,
    get_perfil_activo,
)
from backend.pipeline import procesar_vacantes, importar_raw_data
from backend.scrapers.getonbord import scrape_getonbord

app = FastAPI(title="Job Tracker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


class PerfilCreate(BaseModel):
    nombre: str
    keywords_incluir: list[str]
    keywords_excluir: list[str]
    cv_texto: str
    linkedin_search_string: Optional[str] = ""
    getonbord_tags: Optional[list[str]] = []


class PerfilUpdate(BaseModel):
    nombre: Optional[str] = None
    keywords_incluir: Optional[list[str]] = None
    keywords_excluir: Optional[list[str]] = None
    cv_texto: Optional[str] = None
    linkedin_search_string: Optional[str] = None
    getonbord_tags: Optional[list[str]] = None


class EstadoUpdate(BaseModel):
    estado: str


class NotasUpdate(BaseModel):
    notas: str


@app.get("/perfiles")
def listar_perfiles():
    return get_perfiles()


@app.post("/perfiles", status_code=201)
def crear_perfil(data: PerfilCreate):
    return create_perfil(data.model_dump())


@app.put("/perfiles/{perfil_id}")
def editar_perfil(perfil_id: int, data: PerfilUpdate):
    perfil = get_perfil(perfil_id)
    if not perfil:
        raise HTTPException(404, "Perfil no encontrado")
    return update_perfil(perfil_id, data.model_dump(exclude_none=True))


@app.put("/perfiles/{perfil_id}/activar")
def activar(perfil_id: int):
    perfil = get_perfil(perfil_id)
    if not perfil:
        raise HTTPException(404, "Perfil no encontrado")
    return activar_perfil(perfil_id)


@app.get("/aplicaciones")
def listar_aplicaciones(
    estado: Optional[str] = None,
    perfil_id: Optional[int] = None,
    fuente: Optional[str] = None,
):
    return get_aplicaciones(estado=estado, perfil_id=perfil_id, fuente=fuente)


@app.get("/aplicaciones/{app_id}")
def detalle_aplicacion(app_id: int):
    app = get_aplicacion(app_id)
    if not app:
        raise HTTPException(404, "Aplicación no encontrada")
    return app


@app.put("/aplicaciones/{app_id}/estado")
def cambiar_estado(app_id: int, data: EstadoUpdate):
    try:
        return update_estado(app_id, data.estado)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.put("/aplicaciones/{app_id}/notas")
def agregar_notas(app_id: int, data: NotasUpdate):
    return update_notas(app_id, data.notas)


@app.delete("/aplicaciones/{app_id}", status_code=204)
def eliminar_aplicacion(app_id: int):
    delete_aplicacion(app_id)


@app.post("/pipeline/run")
async def run_pipeline():
    """Ejecuta scrapers GetOnBord + pipeline de filtros con el perfil activo."""
    perfil = get_perfil_activo()
    if not perfil:
        raise HTTPException(400, "No hay perfil activo")

    tags = json.loads(perfil.get("getonbord_tags", "[]"))
    vacantes = await scrape_getonbord(tags)

    if not vacantes:
        return {"mensaje": "No se encontraron vacantes en GetOnBord", "tags": tags}

    stats = procesar_vacantes(vacantes, fuente="getonbord")
    return stats


@app.post("/pipeline/importar-raw")
def importar_raw():
    """Procesa JSONs de raw_data/ generados por la extensión Chrome."""
    return importar_raw_data()


@app.get("/stats")
def estadisticas():
    return get_stats()


@app.get("/health")
def health():
    return {"status": "ok"}
