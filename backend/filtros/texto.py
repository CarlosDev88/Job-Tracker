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


def patron_empresa(nombre: str | None):
    """Compila el patron para reconocer una empresa vetada escrita de cualquier
    forma: 'BairesDev', 'Baires Dev', 'BAIRESDEV S.A.' o 'Baires-Dev'.

    Se permite cualquier separador ENTRE los caracteres, pero se exige que el
    nombre empiece y termine en frontera de palabra. Sin esa frontera, un match
    por subcadena convierte 'HP' en algo que descarta 'PHP Developer' y 'IT' en
    algo que descarta 'Digital Solutions' — y como la purga borra del historico,
    esa perdida seria permanente."""
    base = re.sub(r"[^a-z0-9]", "", normalizar_texto(nombre))
    if not base:
        return None
    cuerpo = r"[^a-z0-9]*".join(re.escape(caracter) for caracter in base)
    return re.compile(r"(?<![a-z0-9])" + cuerpo + r"(?![a-z0-9])")


def compilar_bloqueadas(empresas_bloqueadas) -> list:
    return [p for p in (patron_empresa(e) for e in (empresas_bloqueadas or [])) if p]


def texto_identidad(empresa: str | None, titulo: str | None) -> str:
    """Empresa y titulo juntos: en los avisos de reclutadores la empresa suele
    venir vacia y el nombre aparece solo en el titulo. El separador evita que un
    patron haga match cruzando el final de uno con el principio del otro."""
    return normalizar_texto(empresa) + " | " + normalizar_texto(titulo)


def esta_bloqueada(vacante: dict, empresas_bloqueadas) -> bool:
    """True si la vacante pertenece a una empresa vetada."""
    return coincide_bloqueada(
        vacante.get("empresa"), vacante.get("titulo"),
        compilar_bloqueadas(empresas_bloqueadas),
    )


def coincide_bloqueada(empresa, titulo, patrones) -> bool:
    """Variante que recibe los patrones ya compilados, para no recompilarlos en
    cada fila cuando se recorre el historico completo."""
    if not patrones:
        return False
    texto = texto_identidad(empresa, titulo)
    return any(patron.search(texto) for patron in patrones)


def contiene(texto: str, termino: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(termino) + r"(?!\w)", texto))


# Esquemas que el frontend puede poner en un href sin riesgo. Los datos vienen
# de paginas de terceros, y un link "javascript:..." colado en un JSON del
# scraper se convertiria en ejecucion de codigo al hacer clic, en el mismo
# origen donde viven el CV y el historial de postulaciones.
PATRON_ESQUEMA = re.compile(r"^[a-z][a-z0-9+.\-]*:", re.IGNORECASE)


def canonicalizar_link(link: str | None) -> str:
    if not link:
        return ""
    link = str(link).strip()
    if not re.match(r"https?://", link, re.IGNORECASE):
        # Sin esquema puede ser una ruta relativa o un dominio suelto: se deja.
        # Con un esquema que no sea http(s), se descarta.
        return "" if PATRON_ESQUEMA.match(link) else link.rstrip("/")

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


# Un link a un perfil de persona (linkedin.com/in/...) identifica al autor del
# post, no a la vacante: el scraper lo usa como link cuando el aviso no trae uno
# propio. Si se tomara como identidad, todas las vacantes que publique un mismo
# reclutador colapsarian en un unico registro y se perderian las demas.
PATRON_PERFIL_PERSONA = re.compile(
    r"^https?://([a-z0-9-]+\.)*linkedin\.com/(in|pub)/", re.IGNORECASE)


def es_link_de_perfil(link: str | None) -> bool:
    return bool(link) and bool(PATRON_PERFIL_PERSONA.match(link.strip()))


def generar_dedupe_key(vacante: dict) -> str:
    link = canonicalizar_link(vacante.get("link"))
    if es_link_de_perfil(link):
        link = ""
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
