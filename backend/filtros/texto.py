import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "trackingid", "refid", "trk",
}


def normalizar_texto(texto: str | None) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", texto).strip().lower()


def contiene(texto: str, termino: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(termino) + r"(?!\w)", texto))


def canonicalizar_link(link: str | None) -> str:
    if not link:
        return ""
    link = str(link).strip()
    if not re.match(r"https?://", link, re.IGNORECASE):
        return link.rstrip("/")

    parsed = urlparse(link)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    linkedin_job = re.search(r"/jobs/view/(\d+)", path)
    if host.endswith("linkedin.com") and linkedin_job:
        return f"https://www.linkedin.com/jobs/view/{linkedin_job.group(1)}"

    return urlunparse((
        parsed.scheme.lower(),
        host,
        path,
        "",
        urlencode(query, doseq=True),
        "",
    ))


def normalizar_titulo_dedupe(titulo: str | None) -> str:
    """Título normalizado para comparar identidad de vacante, sin la referencia
    interna del reclutador (REF#1234, Ref. 5678, etc.) que cambia entre reposts
    del mismo aviso aunque el resto del contenido sea idéntico."""
    texto = normalizar_texto(titulo)
    texto = re.sub(r"\bref\.?\s*#?\s*\d+\b", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def generar_dedupe_key(vacante: dict) -> str:
    link = canonicalizar_link(vacante.get("link"))
    if link:
        base = f"link|{link}"
    else:
        # No se incluye "fuente": la misma vacante publicada tanto en la búsqueda
        # de LinkedIn como en publicaciones sueltas debe colapsar a un solo registro.
        base = "|".join([
            normalizar_texto(vacante.get("titulo")),
            normalizar_texto(vacante.get("empresa")),
            normalizar_texto(vacante.get("descripcion"))[:1000],
        ])
    return "sha256:" + hashlib.sha256(base.encode("utf-8")).hexdigest()
