from backend.filtros.feed_filter import clasificar_post_feed


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
        "link": links[0] if links else item.get("autor_perfil", ""),
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
            "titulo": item.get("titulo", ""),
            "empresa": item.get("empresa", ""),
            "ubicacion": item.get("ubicacion", ""),
            "descripcion": item.get("descripcion", ""),
            "link": item.get("link", ""),
            "extraido_en": item.get("extraido_en", ""),
            "imagenes": item.get("imagenes") or [],
            "contactos": {"emails": [], "links": []},
        }

    if item.get("tiene_tarjeta_empleo") and item.get("tarjeta_empleo"):
        tarjeta = item["tarjeta_empleo"]
        return {
            "tipo_resultado": "vacante",
            "titulo": tarjeta.get("titulo", ""),
            "empresa": tarjeta.get("empresa", ""),
            "ubicacion": tarjeta.get("ubicacion", ""),
            "descripcion": item.get("descripcion") or tarjeta.get("descripcion", ""),
            "link": tarjeta.get("link", ""),
            "extraido_en": item.get("extraido_en", ""),
            "imagenes": item.get("imagenes") or [],
            "contactos": {"emails": [], "links": []},
        }

    return _post_textual(item)
