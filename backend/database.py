import sqlite3
import json
import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DATABASE_URL", "./job_tracker.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS perfiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            keywords_incluir TEXT NOT NULL,
            keywords_excluir TEXT NOT NULL,
            cv_texto TEXT NOT NULL,
            linkedin_search_string TEXT,
            getonbord_tags TEXT,
            activo INTEGER DEFAULT 0,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            perfil_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            empresa TEXT,
            ubicacion TEXT,
            descripcion TEXT,
            link TEXT UNIQUE NOT NULL,
            fuente TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            score_detalle TEXT,
            llm_razon TEXT,
            estado TEXT DEFAULT 'pendiente',
            fecha_encontrada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_aplicacion TIMESTAMP,
            notas TEXT,
            FOREIGN KEY (perfil_id) REFERENCES perfiles(id)
        );
    """)

    columnas = [row["name"] for row in cursor.execute("PRAGMA table_info(job_applications)")]
    if "gemini_razon" in columnas and "llm_razon" not in columnas:
        cursor.execute("ALTER TABLE job_applications RENAME COLUMN gemini_razon TO llm_razon")

    existing = cursor.execute(
        "SELECT id FROM perfiles WHERE nombre = 'Frontend React Senior'"
    ).fetchone()
    if not existing:
        cursor.execute(
            """
            INSERT INTO perfiles (nombre, keywords_incluir, keywords_excluir, cv_texto, linkedin_search_string, getonbord_tags, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "Frontend React Senior",
                json.dumps(
                    ["react", "typescript", "next.js", "frontend", "jsx", "tailwind"]
                ),
                json.dumps(
                    [
                        "angular",
                        "vue",
                        "java",
                        "c#",
                        ".net",
                        "backend",
                        "fullstack",
                        "full stack",
                        "entry level",
                        "junior",
                        "spring",
                        "odoo",
                        "django",
                    ]
                ),
                "Senior Frontend Engineer con 5 años de experiencia en React, TypeScript, Next.js. Proyectos en e-commerce (VTEX, Carrefour, Cencosud) y fintech. Experiencia con Tailwind, Zustand, Module Federation, Storybook.",
                '"Frontend" "React" Colombia remoto -"Full Stack" -"Fullstack" -"Backend"',
                json.dumps(["react-js", "typescript"]),
                1,
            ),
        )

    conn.commit()
    conn.close()
    print(f"DB inicializada en {DB_PATH}")


def get_perfiles():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM perfiles ORDER BY activo DESC, creado_en DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_perfil(perfil_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM perfiles WHERE id = ?", (perfil_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_perfil_activo():
    conn = get_connection()
    row = conn.execute("SELECT * FROM perfiles WHERE activo = 1 LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


def create_perfil(data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO perfiles (nombre, keywords_incluir, keywords_excluir, cv_texto, linkedin_search_string, getonbord_tags, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data["nombre"],
            json.dumps(data.get("keywords_incluir", [])),
            json.dumps(data.get("keywords_excluir", [])),
            data["cv_texto"],
            data.get("linkedin_search_string", ""),
            json.dumps(data.get("getonbord_tags", [])),
            0,
        ),
    )
    conn.commit()
    perfil_id = cursor.lastrowid
    conn.close()
    return get_perfil(perfil_id)


def update_perfil(perfil_id: int, data: dict):
    conn = get_connection()
    fields = []
    values = []
    for key in [
        "nombre",
        "keywords_incluir",
        "keywords_excluir",
        "cv_texto",
        "linkedin_search_string",
        "getonbord_tags",
    ]:
        if key in data:
            fields.append(f"{key} = ?")
            val = data[key]
            values.append(json.dumps(val) if isinstance(val, list) else val)
    if not fields:
        conn.close()
        return get_perfil(perfil_id)
    values.append(perfil_id)
    conn.execute(f"UPDATE perfiles SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return get_perfil(perfil_id)


def activar_perfil(perfil_id: int):
    conn = get_connection()
    conn.execute("UPDATE perfiles SET activo = 0")
    conn.execute("UPDATE perfiles SET activo = 1 WHERE id = ?", (perfil_id,))
    conn.commit()
    conn.close()
    return get_perfil(perfil_id)


def _normalizar_link(link: str) -> str:
    """Quita query string y '/' final para que la misma vacante con distintos
    parámetros de tracking no se cuele como fila duplicada (UNIQUE en link)."""
    return link.split("?")[0].rstrip("/")


def create_aplicacion(data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO job_applications
            (perfil_id, titulo, empresa, ubicacion, descripcion, link, fuente, score, score_detalle, llm_razon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                data["perfil_id"],
                data["titulo"],
                data.get("empresa", ""),
                data.get("ubicacion", ""),
                data.get("descripcion", ""),
                _normalizar_link(data["link"]),
                data["fuente"],
                data.get("score", 0),
                json.dumps(data.get("score_detalle", {})),
                data.get("llm_razon", ""),
            ),
        )
        conn.commit()
        app_id = cursor.lastrowid
        conn.close()
        return get_aplicacion(app_id)
    except sqlite3.IntegrityError:
        conn.close()
        return None  # Duplicado por link UNIQUE


def get_aplicacion(app_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM job_applications WHERE id = ?", (app_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_aplicaciones(
    estado: Optional[str] = None,
    perfil_id: Optional[int] = None,
    fuente: Optional[str] = None,
):
    conn = get_connection()
    query = "SELECT * FROM job_applications WHERE 1=1"
    params = []
    if estado:
        query += " AND estado = ?"
        params.append(estado)
    if perfil_id:
        query += " AND perfil_id = ?"
        params.append(perfil_id)
    if fuente:
        query += " AND fuente = ?"
        params.append(fuente)
    query += " ORDER BY score DESC, fecha_encontrada DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_estado(app_id: int, estado: str):
    estados_validos = [
        "pendiente",
        "aplicado",
        "cv_enviado",
        "hr_contacto",
        "prueba_tecnica",
        "entrevista_rrhh",
        "entrevista_tecnica",
        "oferta",
        "rechazado",
        "ghosted",
    ]
    if estado not in estados_validos:
        raise ValueError(f"Estado inválido: {estado}")
    conn = get_connection()
    conn.execute(
        "UPDATE job_applications SET estado = ? WHERE id = ?", (estado, app_id)
    )
    if estado in ["aplicado", "cv_enviado"]:
        conn.execute(
            "UPDATE job_applications SET fecha_aplicacion = ? WHERE id = ?",
            (datetime.now().isoformat(), app_id),
        )
    conn.commit()
    conn.close()
    return get_aplicacion(app_id)


def update_notas(app_id: int, notas: str):
    conn = get_connection()
    conn.execute("UPDATE job_applications SET notas = ? WHERE id = ?", (notas, app_id))
    conn.commit()
    conn.close()
    return get_aplicacion(app_id)


def delete_aplicacion(app_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM job_applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM job_applications").fetchone()["c"]
    por_estado = conn.execute("""
        SELECT estado, COUNT(*) as count FROM job_applications GROUP BY estado
    """).fetchall()
    por_fuente = conn.execute("""
        SELECT fuente, COUNT(*) as count FROM job_applications GROUP BY fuente
    """).fetchall()
    por_dia = conn.execute("""
        SELECT DATE(fecha_encontrada) as dia, COUNT(*) as count
        FROM job_applications
        GROUP BY dia ORDER BY dia DESC LIMIT 30
    """).fetchall()
    conn.close()
    return {
        "total": total,
        "por_estado": [dict(r) for r in por_estado],
        "por_fuente": [dict(r) for r in por_fuente],
        "por_dia": [dict(r) for r in por_dia],
    }
