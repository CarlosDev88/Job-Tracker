import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "trackingid", "refid", "trk",
}


def sanear_estructura(valor):
    """Corrige caracteres inválidos (surrogates sueltos de emojis rotos que
    llegan del scraper) en cualquier string/dict/list anidado, para que ni el
    JSON ni SQLite truenen al guardarlos."""
    if isinstance(valor, str):
        return valor.encode("utf-8", "replace").decode("utf-8")
    if isinstance(valor, dict):
        return {clave: sanear_estructura(item) for clave, item in valor.items()}
    if isinstance(valor, list):
        return [sanear_estructura(item) for item in valor]
    return valor


def normalizar_texto(texto: str | None) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", texto).strip().lower()


def normalizar_identidad(texto: str | None) -> str:
    """Normaliza un nombre de empresa a su forma más comparable: sin tildes,
    minúsculas y sin espacios ni puntuación. Así 'Baires Dev', 'BairesDev LLC'
    y 'BAIRESDEV S.A.' colapsan todas a algo que contiene 'bairesdev'."""
    return re.sub(r"[^a-z0-9]", "", normalizar_texto(texto))


def esta_bloqueada(vacante: dict, empresas_bloqueadas) -> bool:
    """True si la vacante pertenece a una empresa vetada. Compara contra
    empresa y título (donde suelen aparecer los avisos de reclutadores)."""
    if not empresas_bloqueadas:
        return False
    campos = normalizar_identidad(vacante.get("empresa")) + "|" + normalizar_identidad(vacante.get("titulo"))
    for empresa in empresas_bloqueadas:
        clave = normalizar_identidad(empresa)
        if clave and clave in campos:
            return True
    return False


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
