from backend.filtros.feed_filter import clasificar_post_feed


def _clasificar_post_textual(item: dict) -> dict | None:
    """
    Posts del feed de LinkedIn sin tarjeta_empleo estructurada: pasan por el
    filtro dedicado de feed_filter.py (algoritmo_feed.md) en vez del filtro
    genérico de keywords.py — el caption es demasiado corto para que el
    score/gaps genérico funcione bien. La decisión (REVISAR/TAL_VEZ), el
    score y el contacto extraído (emails/links) quedan en el dict resultante
    para que pipeline.py los use directo, sin volver a correr filtrar_vacante.
    """
    descripcion = item.get("descripcion") or ""
    resultado = clasificar_post_feed(descripcion)
    if resultado is None:
        return None

    links = resultado["links"]
    return {
        "titulo": descripcion.strip().splitlines()[0][:120] if descripcion.strip() else "(revisar manualmente)",
        "empresa": "",
        "ubicacion": "",
        "descripcion": descripcion,
        "link": links[0] if links else item.get("autor_perfil", ""),
        "extraido_en": item.get("extraido_en", ""),
        "revisar_manual": True,
        "imagenes": item.get("imagenes") or [],
        "feed_decision": resultado["decision"],
        "feed_score": resultado["score"],
        "feed_emails": resultado["emails"],
        "feed_links": links,
    }


def normalizar_vacante(item: dict, fuente: str) -> dict | None:
    """
    Normaliza un item de raw_data a la forma estándar
    {titulo, empresa, ubicacion, descripcion, link, extraido_en}.

    `fuente` viene del nombre del archivo (ver _detectar_fuente en pipeline.py)
    y es lo que decide si un item necesita pasar por esta lógica de detección
    de "¿esto es una vacante?": solo linkedin_feed mezcla posts normales con
    posts que traen tarjeta_empleo y posts que anuncian una vacante en texto
    libre sin tarjeta. Los demás archivos (linkedin_extension, getonbrd,
    linkedin_publicaciones) ya vienen pre-estructurados como vacante — se
    devuelven tal cual, sin gastar ni un regex ni una llamada al LLM.
    """
    if fuente != "linkedin_feed":
        return item

    if item.get("tiene_tarjeta_empleo") and item.get("tarjeta_empleo"):
        tarjeta = item["tarjeta_empleo"]
        return {
            "titulo": tarjeta.get("titulo", ""),
            "empresa": tarjeta.get("empresa", ""),
            "ubicacion": tarjeta.get("ubicacion", ""),
            "descripcion": item.get("descripcion", ""),
            "link": tarjeta.get("link", ""),
            "extraido_en": item.get("extraido_en", ""),
            "imagenes": item.get("imagenes") or [],
        }

    return _clasificar_post_textual(item)
