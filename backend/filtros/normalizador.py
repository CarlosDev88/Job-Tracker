from backend.filtros.feed_filter import clasificar_post_feed


def _texto(valor) -> str:
    """El scraper emite null en campos de texto (empresa, ubicacion y a veces
    descripcion). dict.get(clave, "") NO protege de eso: si la clave existe con
    valor null devuelve None, y un solo item asi tumbaba el pipeline entero."""
    return valor if isinstance(valor, str) else ""


def _post_textual(item: dict) -> dict | None:
    descripcion = item.get("descripcion") or ""
    resultado = clasificar_post_feed(descripcion)
    if resultado is None:
        return None
    links = resultado["links"]
    return {
        "tipo_resultado": "feed_post",
        "titulo": descripcion.strip().splitlines()[0][:120] if descripcion.strip() else "(revisar manualmente)",
        "empresa": "",
        "ubicacion": "",
        "descripcion": descripcion,
        "link": links[0] if links else "",
        "extraido_en": item.get("extraido_en", ""),
        "imagenes": item.get("imagenes") or [],
        "contactos": {"emails": resultado["emails"], "links": links},
        "feed_decision": resultado["decision"],
        "feed_score": resultado["score"],
    }


def normalizar_vacante(item: dict, fuente: str) -> dict | None:
    if fuente != "linkedin_feed":
        return {
            "tipo_resultado": "vacante",
            "titulo": _texto(item.get("titulo")),
            "empresa": _texto(item.get("empresa")),
            "ubicacion": _texto(item.get("ubicacion")),
            "descripcion": _texto(item.get("descripcion")),
            "link": _texto(item.get("link")),
            "extraido_en": _texto(item.get("extraido_en")),
            "imagenes": item.get("imagenes") or [],
            "contactos": {"emails": [], "links": []},
        }

    tarjeta = item.get("tarjeta_empleo")
    if item.get("tiene_tarjeta_empleo") and isinstance(tarjeta, dict):
        return {
            "tipo_resultado": "vacante",
            "titulo": _texto(tarjeta.get("titulo")),
            "empresa": _texto(tarjeta.get("empresa")),
            "ubicacion": _texto(tarjeta.get("ubicacion")),
            "descripcion": _texto(item.get("descripcion")) or _texto(tarjeta.get("descripcion")),
            "link": _texto(tarjeta.get("link")),
            "extraido_en": _texto(item.get("extraido_en")),
            "imagenes": item.get("imagenes") or [],
            "contactos": {"emails": [], "links": []},
        }

    return _post_textual(item)
