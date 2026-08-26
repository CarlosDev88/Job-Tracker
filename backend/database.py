import json
import os
import sqlite3
from datetime import datetime
from typing import Iterable

from dotenv import load_dotenv

from backend.filtros.texto import canonicalizar_link, generar_dedupe_key

load_dotenv()
DB_PATH = os.getenv("DATABASE_URL", "./job_tracker.db")

ESTADOS_VALIDOS = {
    "pendiente", "aplicado", "cv_enviado", "hr_contacto", "prueba_tecnica",
    "entrevista_rrhh", "entrevista_tecnica", "oferta", "rechazado", "ghosted",
}


def get_connection() -> sqlite3.Connection:
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


def _crear_perfiles(cursor: sqlite3.Cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS perfiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            keywords_incluir TEXT NOT NULL DEFAULT '[]',
            keywords_excluir TEXT NOT NULL DEFAULT '[]',
            cv_texto TEXT NOT NULL DEFAULT '',
            ubicacion_base TEXT NOT NULL DEFAULT 'Bucaramanga',
            activo INTEGER NOT NULL DEFAULT 0,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    columnas = {fila["name"] for fila in cursor.execute("PRAGMA table_info(perfiles)")}
    if "ubicacion_base" not in columnas:
        cursor.execute("ALTER TABLE perfiles ADD COLUMN ubicacion_base TEXT NOT NULL DEFAULT 'Bucaramanga'")


def _crear_aplicaciones(cursor: sqlite3.Cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            perfil_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            empresa TEXT NOT NULL DEFAULT '',
            ubicacion TEXT NOT NULL DEFAULT '',
            descripcion TEXT NOT NULL DEFAULT '',
            link TEXT NOT NULL DEFAULT '',
            dedupe_key TEXT NOT NULL UNIQUE,
            fuente TEXT NOT NULL DEFAULT '',
            score INTEGER NOT NULL DEFAULT 0,
            score_detalle TEXT NOT NULL DEFAULT '{}',
            estado TEXT NOT NULL DEFAULT 'pendiente',
            fecha_encontrada TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fecha_aplicacion TIMESTAMP,
            notas TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (perfil_id) REFERENCES perfiles(id)
        )
    """)


def _migrar_aplicaciones(cursor: sqlite3.Cursor) -> None:
    existe = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='job_applications'"
    ).fetchone()
    if not existe:
        _crear_aplicaciones(cursor)
        return

    columnas = {fila["name"] for fila in cursor.execute("PRAGMA table_info(job_applications)")}
    if "dedupe_key" in columnas:
        return

    filas = [dict(fila) for fila in cursor.execute("SELECT * FROM job_applications")]
    cursor.execute("ALTER TABLE job_applications RENAME TO job_applications_legacy")
    _crear_aplicaciones(cursor)

    usados = set()
    for fila in filas:
        key = generar_dedupe_key(fila)
        while key in usados:
            key = f"{key}:{fila['id']}"
        usados.add(key)
        cursor.execute("""
            INSERT INTO job_applications (
                perfil_id, titulo, empresa, ubicacion, descripcion, link, dedupe_key,
                fuente, score, score_detalle, estado, fecha_encontrada,
                fecha_aplicacion, notas
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fila["perfil_id"], fila.get("titulo", ""), fila.get("empresa", ""),
            fila.get("ubicacion", ""), fila.get("descripcion", ""),
            canonicalizar_link(fila.get("link", "")), key,
            fila.get("fuente", ""), fila.get("score", 0),
            fila.get("score_detalle", "{}"), fila.get("estado", "pendiente"),
            fila.get("fecha_encontrada") or datetime.now().isoformat(),
            fila.get("fecha_aplicacion"), fila.get("notas", ""),
        ))
    cursor.execute("DROP TABLE job_applications_legacy")


def init_db() -> None:
    conexion = get_connection()
    cursor = conexion.cursor()
    _crear_perfiles(cursor)
    _migrar_aplicaciones(cursor)

    existe = cursor.execute("SELECT id FROM perfiles WHERE activo = 1 LIMIT 1").fetchone()
    if not existe:
        cursor.execute("""
            INSERT INTO perfiles (nombre, keywords_incluir, keywords_excluir, cv_texto, ubicacion_base, activo)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (
            "Frontend React Senior",
            json.dumps(["react", "typescript", "next.js", "frontend", "tailwind"]),
            json.dumps(["angular", "java", ".net", "backend", "fullstack", "junior"]),
            "Perfil de frontend React con experiencia en TypeScript, Next.js y e-commerce.",
            "Bucaramanga",
        ))
    conexion.commit()
    conexion.close()


def _dict(fila: sqlite3.Row | None) -> dict | None:
    return dict(fila) if fila else None


def get_perfil_activo() -> dict | None:
    conexion = get_connection()
    fila = conexion.execute("SELECT * FROM perfiles WHERE activo = 1 LIMIT 1").fetchone()
    conexion.close()
    return _dict(fila)


def update_perfil_activo(data: dict) -> dict | None:
    permitido = {"nombre", "keywords_incluir", "keywords_excluir", "cv_texto", "ubicacion_base"}
    campos, valores = [], []
    for clave in permitido:
        if clave in data:
            valor = data[clave]
            campos.append(f"{clave} = ?")
            valores.append(json.dumps(valor) if isinstance(valor, list) else valor)
    if not campos:
        return get_perfil_activo()

    perfil = get_perfil_activo()
    if not perfil:
        return None
    valores.append(perfil["id"])
    conexion = get_connection()
    conexion.execute(f"UPDATE perfiles SET {', '.join(campos)} WHERE id = ?", valores)
    conexion.commit()
    conexion.close()
    return get_perfil_activo()


def create_aplicacion(data: dict) -> dict | None:
    perfil = get_perfil_activo()
    if not perfil:
        raise ValueError("No hay perfil activo")

    estado = data.get("estado_inicial", "pendiente")
    if estado not in {"pendiente", "aplicado"}:
        raise ValueError("El estado inicial debe ser pendiente o aplicado")

    dedupe_key = data.get("dedupe_key") or generar_dedupe_key(data)
    conexion = get_connection()
    existe = conexion.execute(
        "SELECT id FROM job_applications WHERE dedupe_key = ?", (dedupe_key,)
    ).fetchone()
    if existe:
        conexion.close()
        return None

    fecha_aplicacion = datetime.now().isoformat() if estado == "aplicado" else None
    cursor = conexion.execute("""
        INSERT INTO job_applications (
            perfil_id, titulo, empresa, ubicacion, descripcion, link, dedupe_key,
            fuente, score, score_detalle, estado, fecha_aplicacion
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        perfil["id"], data.get("titulo", ""), data.get("empresa", ""),
        data.get("ubicacion", ""), data.get("descripcion", ""),
        canonicalizar_link(data.get("link")), dedupe_key,
        data.get("fuente", ""), data.get("score", 0),
        json.dumps(data.get("score_detalle", {}), ensure_ascii=False),
        estado, fecha_aplicacion,
    ))
    aplicacion_id = cursor.lastrowid
    conexion.commit()
    conexion.close()
    return get_aplicacion(aplicacion_id)


def get_aplicacion(aplicacion_id: int) -> dict | None:
    conexion = get_connection()
    fila = conexion.execute("SELECT * FROM job_applications WHERE id = ?", (aplicacion_id,)).fetchone()
    conexion.close()
    return _dict(fila)


def get_aplicaciones(estado: str | None = None, fuente: str | None = None) -> list[dict]:
    consulta, parametros = "SELECT * FROM job_applications WHERE 1=1", []
    if estado:
        consulta += " AND estado = ?"
        parametros.append(estado)
    if fuente:
        consulta += " AND fuente = ?"
        parametros.append(fuente)
    consulta += " ORDER BY fecha_encontrada DESC, score DESC"
    conexion = get_connection()
    filas = conexion.execute(consulta, parametros).fetchall()
    conexion.close()
    return [dict(fila) for fila in filas]


def get_tracking_por_claves(claves: Iterable[str]) -> dict[str, dict]:
    claves = list(dict.fromkeys(clave for clave in claves if clave))
    if not claves:
        return {}
    marcadores = ",".join("?" for _ in claves)
    conexion = get_connection()
    filas = conexion.execute(
        f"SELECT id, dedupe_key, estado, fecha_aplicacion FROM job_applications WHERE dedupe_key IN ({marcadores})",
        claves,
    ).fetchall()
    conexion.close()
    return {fila["dedupe_key"]: dict(fila) for fila in filas}


def update_estado(aplicacion_id: int, estado: str) -> dict | None:
    if estado not in ESTADOS_VALIDOS:
        raise ValueError("Estado inválido")
    aplicacion = get_aplicacion(aplicacion_id)
    if not aplicacion:
        return None

    conexion = get_connection()
    if estado in {"aplicado", "cv_enviado"} and not aplicacion.get("fecha_aplicacion"):
        conexion.execute(
            "UPDATE job_applications SET estado = ?, fecha_aplicacion = ? WHERE id = ?",
            (estado, datetime.now().isoformat(), aplicacion_id),
        )
    else:
        conexion.execute("UPDATE job_applications SET estado = ? WHERE id = ?", (estado, aplicacion_id))
    conexion.commit()
    conexion.close()
    return get_aplicacion(aplicacion_id)


def update_notas(aplicacion_id: int, notas: str) -> dict | None:
    if not get_aplicacion(aplicacion_id):
        return None
    conexion = get_connection()
    conexion.execute("UPDATE job_applications SET notas = ? WHERE id = ?", (notas, aplicacion_id))
    conexion.commit()
    conexion.close()
    return get_aplicacion(aplicacion_id)


def delete_aplicacion(aplicacion_id: int) -> bool:
    conexion = get_connection()
    cursor = conexion.execute("DELETE FROM job_applications WHERE id = ?", (aplicacion_id,))
    conexion.commit()
    conexion.close()
    return cursor.rowcount > 0


def get_stats() -> dict:
    conexion = get_connection()
    total = conexion.execute("SELECT COUNT(*) AS count FROM job_applications").fetchone()["count"]
    por_estado = [dict(fila) for fila in conexion.execute(
        "SELECT estado, COUNT(*) AS count FROM job_applications GROUP BY estado ORDER BY estado"
    )]
    por_fuente = [dict(fila) for fila in conexion.execute(
        "SELECT fuente, COUNT(*) AS count FROM job_applications GROUP BY fuente ORDER BY fuente"
    )]
    conexion.close()
    return {"total": total, "por_estado": por_estado, "por_fuente": por_fuente}
