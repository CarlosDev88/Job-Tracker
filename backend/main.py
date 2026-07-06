from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

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
)
from backend.pipeline import filtrar_raw_data, analizar_con_llm, leer_filtradas, convertir_a_oferta

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


class AnalizarRequest(BaseModel):
    links: Optional[list[str]] = None


class VacanteAplicar(BaseModel):
    titulo: str
    empresa: Optional[str] = ""
    ubicacion: Optional[str] = ""
    descripcion: Optional[str] = ""
    link: str
    fuente: Optional[str] = ""
    score: Optional[int] = 0
    detalle: Optional[dict] = {}


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


@app.post("/pipeline/filtrar")
def filtrar():
    """Etapa 1: aplica el filtro de keywords a raw_data/ y rankea el resultado en filtradas.json."""
    return filtrar_raw_data()


@app.get("/pipeline/filtradas")
def filtradas():
    """Devuelve el ranking de la última corrida de --filtrar, tal cual quedó en filtradas.json."""
    return leer_filtradas()


@app.post("/pipeline/analizar")
def analizar(data: AnalizarRequest = AnalizarRequest()):
    """
    Etapa 2: corre el filtro semántico del LLM sobre filtradas.json y guarda en la DB.
    Si `data.links` viene con valores, solo analiza esas vacantes (selección manual).
    """
    return analizar_con_llm(links=data.links)


@app.post("/pipeline/aplicar")
def aplicar(data: VacanteAplicar):
    """Convierte una vacante prefiltrada en una oferta con estado 'aplicado', lista para trackear."""
    resultado = convertir_a_oferta(data.model_dump())
    if resultado.get("error"):
        raise HTTPException(400, resultado["error"])
    return resultado


@app.get("/stats")
def estadisticas():
    return get_stats()


@app.get("/health")
def health():
    return {"status": "ok"}
