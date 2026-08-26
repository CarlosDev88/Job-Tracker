from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.database import (
    create_aplicacion,
    delete_aplicacion,
    get_aplicacion,
    get_aplicaciones,
    get_perfil_activo,
    get_stats,
    init_db,
    update_estado,
    update_notas,
    update_perfil_activo,
)
from backend.pipeline import filtrar_raw_data, leer_filtradas

app = FastAPI(title="Job Tracker API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


class PerfilUpdate(BaseModel):
    nombre: str | None = None
    keywords_incluir: list[str] | None = None
    keywords_excluir: list[str] | None = None
    cv_texto: str | None = None
    ubicacion_base: str | None = None


class AplicacionCreate(BaseModel):
    dedupe_key: str = Field(min_length=1)
    titulo: str = ""
    empresa: str = ""
    ubicacion: str = ""
    descripcion: str = Field(min_length=1)
    link: str = ""
    fuente: str = ""
    score: int = 0
    score_detalle: dict = Field(default_factory=dict)
    estado_inicial: Literal["pendiente", "aplicado"] = "pendiente"


class EstadoUpdate(BaseModel):
    estado: str


class NotasUpdate(BaseModel):
    notas: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/perfil")
def perfil() -> dict:
    perfil_activo = get_perfil_activo()
    if not perfil_activo:
        raise HTTPException(404, "Perfil no encontrado")
    return perfil_activo


@app.put("/perfil")
def editar_perfil(data: PerfilUpdate) -> dict:
    perfil_activo = update_perfil_activo(data.model_dump(exclude_none=True))
    if not perfil_activo:
        raise HTTPException(404, "Perfil no encontrado")
    return perfil_activo


@app.post("/pipeline/filtrar")
def filtrar() -> dict:
    resultado = filtrar_raw_data()
    if resultado.get("error"):
        raise HTTPException(400, resultado["error"])
    return resultado


@app.get("/pipeline/filtradas")
def filtradas() -> dict:
    return leer_filtradas()


@app.post("/aplicaciones", status_code=201)
def guardar_aplicacion(data: AplicacionCreate) -> dict:
    try:
        creada = create_aplicacion(data.model_dump())
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    if creada is None:
        raise HTTPException(409, "La vacante ya está guardada")
    return creada


@app.get("/aplicaciones")
def listar_aplicaciones(estado: str | None = None, fuente: str | None = None) -> list[dict]:
    return get_aplicaciones(estado=estado, fuente=fuente)


@app.get("/aplicaciones/{aplicacion_id}")
def detalle_aplicacion(aplicacion_id: int) -> dict:
    aplicacion = get_aplicacion(aplicacion_id)
    if not aplicacion:
        raise HTTPException(404, "Vacante no encontrada")
    return aplicacion


@app.put("/aplicaciones/{aplicacion_id}/estado")
def cambiar_estado(aplicacion_id: int, data: EstadoUpdate) -> dict:
    try:
        aplicacion = update_estado(aplicacion_id, data.estado)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    if not aplicacion:
        raise HTTPException(404, "Vacante no encontrada")
    return aplicacion


@app.put("/aplicaciones/{aplicacion_id}/notas")
def guardar_notas(aplicacion_id: int, data: NotasUpdate) -> dict:
    aplicacion = update_notas(aplicacion_id, data.notas)
    if not aplicacion:
        raise HTTPException(404, "Vacante no encontrada")
    return aplicacion


@app.delete("/aplicaciones/{aplicacion_id}", status_code=204)
def eliminar_aplicacion(aplicacion_id: int) -> None:
    if not delete_aplicacion(aplicacion_id):
        raise HTTPException(404, "Vacante no encontrada")


@app.get("/stats")
def estadisticas() -> dict:
    return get_stats()
