def normalizar_vacante(item: dict) -> dict | None:
    """
    Normaliza un item de raw_data a la forma estándar
    {titulo, empresa, ubicacion, descripcion, link, extraido_en}.

    El feed de LinkedIn mezcla posts normales con posts que traen una
    tarjeta de empleo embebida (tarjeta_empleo). Un item de ese archivo
    que no sea una vacante real retorna None y se descarta antes de
    llegar al filtro de keywords.
    """
    if "tarjeta_empleo" in item:
        if not item.get("tiene_tarjeta_empleo") or not item.get("tarjeta_empleo"):
            return None
        tarjeta = item["tarjeta_empleo"]
        return {
            "titulo": tarjeta.get("titulo", ""),
            "empresa": tarjeta.get("empresa", ""),
            "ubicacion": tarjeta.get("ubicacion", ""),
            "descripcion": item.get("descripcion", ""),
            "link": tarjeta.get("link", ""),
            "extraido_en": item.get("extraido_en", ""),
        }

    return item
