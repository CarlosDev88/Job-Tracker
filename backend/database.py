import json
import os
import sqlite3
from datetime import datetime
from typing import Iterable

from dotenv import load_dotenv

from backend.filtros.texto import canonicalizar_link, generar_dedupe_key, normalizar_identidad

load_dotenv()
DB_PATH = os.getenv("DATABASE_URL", "./job_tracker.db")

ESTADOS_VALIDOS = {
    "pendiente", "aplicado", "cv_enviado", "hr_contacto", "prueba_tecnica",
    "entrevista_rrhh", "entrevista_tecnica", "oferta", "rechazado", "ghosted",
}


def get_connection() -> sqlite3.Connection:
    conexion = sqlite3.connect(DB_PATH, timeout=30)
    conexion.row_factory = sqlite3.Row
    # WAL: los lectores (conteos, /resultados, /pipeline/filtradas) no se
    # bloquean mientras el pipeline hace su transacción larga de upserts.
    conexion.execute("PRAGMA journal_mode=WAL")
    conexion.execute("PRAGMA busy_timeout=30000")
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
            empresas_bloqueadas TEXT NOT NULL DEFAULT '[]',
            activo INTEGER NOT NULL DEFAULT 0,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    columnas = {fila["name"] for fila in cursor.execute("PRAGMA table_info(perfiles)")}
    if "ubicacion_base" not in columnas:
        cursor.execute("ALTER TABLE perfiles ADD COLUMN ubicacion_base TEXT NOT NULL DEFAULT 'Bucaramanga'")
    if "empresas_bloqueadas" not in columnas:
        cursor.execute("ALTER TABLE perfiles ADD COLUMN empresas_bloqueadas TEXT NOT NULL DEFAULT '[]'")


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


def _crear_resultados(cursor: sqlite3.Cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_resultado TEXT NOT NULL DEFAULT 'vacante',
            titulo TEXT NOT NULL DEFAULT '',
            empresa TEXT NOT NULL DEFAULT '',
            ubicacion TEXT NOT NULL DEFAULT '',
            descripcion TEXT NOT NULL DEFAULT '',
            link TEXT NOT NULL DEFAULT '',
            dedupe_key TEXT NOT NULL UNIQUE,
            fuente TEXT NOT NULL DEFAULT '',
            score INTEGER,
            detalle TEXT NOT NULL DEFAULT '{}',
            primera_vez TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resultados_tipo ON resultados(tipo_resultado)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resultados_fuente ON resultados(fuente)")


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
    _crear_resultados(cursor)

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
    permitido = {"nombre", "keywords_incluir", "keywords_excluir", "cv_texto", "ubicacion_base", "empresas_bloqueadas"}
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


def _sanear_texto(valor):
    """Corrige texto con caracteres inválidos (p. ej. emojis rotos que quedan
    como surrogates sueltos al venir de un scraper) para que SQLite no truene
    al guardarlos."""
    if not isinstance(valor, str):
        return valor
    return valor.encode("utf-8", "replace").decode("utf-8")


def _sanear_estructura(valor):
    if isinstance(valor, str):
        return _sanear_texto(valor)
    if isinstance(valor, dict):
        return {clave: _sanear_estructura(item) for clave, item in valor.items()}
    if isinstance(valor, list):
        return [_sanear_estructura(item) for item in valor]
    return valor


def guardar_resultados(resultados: Iterable[dict]) -> None:
    """Guarda (upsert) los resultados de una corrida del pipeline en la tabla
    resultados. dedupe_key es UNIQUE: si el mismo aviso/post ya existía de una
    corrida anterior se actualiza en el lugar (no se duplica), pero conserva
    su primera_vez original para poder ver el histórico real."""
    conexion = get_connection()
    ahora = datetime.now().isoformat()
    for resultado in resultados:
        conexion.execute("""
            INSERT INTO resultados (
                tipo_resultado, titulo, empresa, ubicacion, descripcion, link,
                dedupe_key, fuente, score, detalle, primera_vez, actualizado_en
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dedupe_key) DO UPDATE SET
                tipo_resultado = excluded.tipo_resultado,
                titulo = excluded.titulo,
                empresa = excluded.empresa,
                ubicacion = excluded.ubicacion,
                descripcion = excluded.descripcion,
                link = excluded.link,
                fuente = excluded.fuente,
                score = excluded.score,
                detalle = excluded.detalle,
                actualizado_en = excluded.actualizado_en
        """, (
            resultado.get("tipo_resultado") or "vacante",
            _sanear_texto(resultado.get("titulo") or ""),
            _sanear_texto(resultado.get("empresa") or ""),
            _sanear_texto(resultado.get("ubicacion") or ""),
            _sanear_texto(resultado.get("descripcion") or ""),
            _sanear_texto(resultado.get("link") or ""),
            resultado["dedupe_key"],
            resultado.get("fuente") or "",
            resultado.get("score"),
            json.dumps(_sanear_estructura(resultado.get("detalle") or {}), ensure_ascii=False),
            ahora, ahora,
        ))
    conexion.commit()
    conexion.close()


def get_resultados(
    tipo_resultado: str | None = None,
    fuente: str | None = None,
    busqueda: str | None = None,
    score_min: int | None = None,
    score_max: int | None = None,
    solo_revisar: bool = False,
    decision: str | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> dict:
    condiciones, parametros = ["1=1"], []

    if tipo_resultado:
        condiciones.append("tipo_resultado = ?")
        parametros.append(tipo_resultado)
    if fuente:
        condiciones.append("fuente = ?")
        parametros.append(fuente)
    if solo_revisar:
        condiciones.append("score IS NULL")
    if score_min is not None:
        condiciones.append("(score IS NOT NULL AND score >= ?)")
        parametros.append(score_min)
    if score_max is not None:
        condiciones.append("(score IS NOT NULL AND score <= ?)")
        parametros.append(score_max)
    if decision:
        condiciones.append("json_extract(detalle, '$.decision') = ?")
        parametros.append(decision)
    if busqueda:
        terminos = [termino for termino in busqueda.strip().split() if termino]
        if terminos:
            partes_termino = []
            for termino in terminos:
                comodin = f"%{termino}%"
                partes_termino.append("(titulo LIKE ? OR empresa LIKE ? OR descripcion LIKE ?)")
                parametros.extend([comodin, comodin, comodin])
            condiciones.append("(" + " OR ".join(partes_termino) + ")")

    where = " AND ".join(condiciones)
    conexion = get_connection()

    total = conexion.execute(f"SELECT COUNT(*) AS count FROM resultados WHERE {where}", parametros).fetchone()["count"]

    pagina = max(1, pagina)
    por_pagina = max(1, min(por_pagina, 100))
    offset = (pagina - 1) * por_pagina
    filas = conexion.execute(f"""
        SELECT * FROM resultados WHERE {where}
        ORDER BY (score IS NULL) ASC, score DESC, primera_vez DESC
        LIMIT ? OFFSET ?
    """, parametros + [por_pagina, offset]).fetchall()

    items = []
    for fila in filas:
        item = dict(fila)
        try:
            item["detalle"] = json.loads(item["detalle"])
        except (TypeError, ValueError):
            item["detalle"] = {}
        items.append(item)

    conexion.close()

    tracking = get_tracking_por_claves([item["dedupe_key"] for item in items])
    for item in items:
        item["tracking"] = tracking.get(item["dedupe_key"])

    return {"items": items, "total": total, "pagina": pagina, "por_pagina": por_pagina}


def purgar_empresas_bloqueadas(empresas_bloqueadas) -> int:
    """Borra del histórico las vacantes de empresas vetadas. Se llama en cada
    corrida del pipeline, así que agregar una empresa a la lista y procesar
    limpia también lo que ya estaba guardado de antes."""
    claves = [normalizar_identidad(empresa) for empresa in (empresas_bloqueadas or [])]
    claves = [clave for clave in claves if clave]
    if not claves:
        return 0

    conexion = get_connection()
    filas = conexion.execute("SELECT id, empresa, titulo FROM resultados").fetchall()
    ids = []
    for fila in filas:
        campos = normalizar_identidad(fila["empresa"]) + "|" + normalizar_identidad(fila["titulo"])
        if any(clave in campos for clave in claves):
            ids.append(fila["id"])

    if ids:
        marcadores = ",".join("?" for _ in ids)
        conexion.execute(f"DELETE FROM resultados WHERE id IN ({marcadores})", ids)
        conexion.commit()
    conexion.close()
    return len(ids)


def get_conteo_resultados() -> dict:
    conexion = get_connection()
    vacantes = conexion.execute(
        "SELECT COUNT(*) AS c FROM resultados WHERE tipo_resultado = 'vacante'"
    ).fetchone()["c"]
    feed = conexion.execute(
        "SELECT COUNT(*) AS c FROM resultados WHERE tipo_resultado = 'feed_post'"
    ).fetchone()["c"]
    pendientes_revisar = conexion.execute(
        "SELECT COUNT(*) AS c FROM resultados WHERE tipo_resultado = 'vacante' AND score IS NULL"
    ).fetchone()["c"]
    conexion.close()
    return {"vacantes": vacantes, "feed": feed, "pendientes_revisar": pendientes_revisar}
