import json
import re

from backend.llm.factory import get_connector

# Red ancha barata: candidatos con lenguaje de contratación, antes de gastar
# una llamada al LLM. Baja precisión a propósito (ver spec: #OpenToWork, ads
# de plataformas de reclutamiento y spam de hashtags también matchean esto)
# — el LLM decide después cuáles son ofertas reales.
PALABRAS_CONTRATACION = re.compile(
    r"buscamos|busco|contratando|contrataci[oó]n|vacante|hiring|"
    r"job opening|oferta laboral|estamos buscando|join our team|"
    r"[uú]nete a nuestro equipo|postul|oportunidad laboral|open position",
    re.IGNORECASE,
)


def _clasificar_post_textual(item: dict) -> dict | None:
    """
    Posts del feed de LinkedIn sin tarjeta_empleo estructurada, pero cuyo
    texto usa lenguaje de contratación. El regex de arriba es una red ancha;
    solo esos candidatos pasan por el LLM, que decide si es una oferta real
    (y no un #OpenToWork, un anuncio de plataforma de reclutamiento, un post
    de opinión, etc.) y extrae título/empresa/ubicación del texto libre.
    """
    descripcion = item.get("descripcion") or ""
    if not PALABRAS_CONTRATACION.search(descripcion):
        return None

    connector = get_connector()
    if not connector.enabled:
        return None

    prompt = f"""Analiza este post de LinkedIn y determina si es una oferta de empleo real (alguien ofreciendo una vacante), y no otra cosa (alguien buscando trabajo, un anuncio de una plataforma de reclutamiento, contenido de opinión, spam de hashtags, etc.).

POST:
{descripcion[:1500]}

Responde SOLO con JSON, sin markdown, sin explicaciones:
{{"es_vacante": true, "titulo": "...", "empresa": "...", "ubicacion": "..."}}

Si es_vacante es false, deja titulo/empresa/ubicacion como cadenas vacías.
"""

    try:
        texto = connector.generar(prompt)
        texto = texto.replace("```json", "").replace("```", "").strip()
        resultado = json.loads(texto)
    except Exception:
        return None

    if not resultado.get("es_vacante"):
        return None

    return {
        "titulo": resultado.get("titulo", ""),
        "empresa": resultado.get("empresa", ""),
        "ubicacion": resultado.get("ubicacion", ""),
        "descripcion": descripcion,
        "link": item.get("autor_perfil", ""),
        "extraido_en": item.get("extraido_en", ""),
    }


def normalizar_vacante(item: dict) -> dict | None:
    """
    Normaliza un item de raw_data a la forma estándar
    {titulo, empresa, ubicacion, descripcion, link, extraido_en}.

    El feed de LinkedIn mezcla posts normales con posts que traen una
    tarjeta de empleo embebida (tarjeta_empleo) y posts que anuncian una
    vacante solo en texto libre, sin tarjeta. Un item de ese archivo que no
    sea una vacante real retorna None y se descarta antes de llegar al
    filtro de keywords.
    """
    if "tarjeta_empleo" in item:
        if item.get("tiene_tarjeta_empleo") and item.get("tarjeta_empleo"):
            tarjeta = item["tarjeta_empleo"]
            return {
                "titulo": tarjeta.get("titulo", ""),
                "empresa": tarjeta.get("empresa", ""),
                "ubicacion": tarjeta.get("ubicacion", ""),
                "descripcion": item.get("descripcion", ""),
                "link": tarjeta.get("link", ""),
                "extraido_en": item.get("extraido_en", ""),
            }
        return _clasificar_post_textual(item)

    return item
