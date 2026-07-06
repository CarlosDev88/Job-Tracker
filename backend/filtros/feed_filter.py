import re
import unicodedata

# Filtro dedicado para posts del feed de LinkedIn sin tarjeta_empleo
# estructurada (ver algoritmo_feed.md) — reemplaza al filtro genérico de
# keywords.py para estos posts. El caption de un post es demasiado corto para
# que el score/gaps genérico (calibrado para publicaciones de empleo
# completas) funcione bien; acá se exigen dos señales (contratación +
# aplicación/contacto) antes de puntuar, lo que elimina falsos positivos tipo
# "buscamos mejorar nuestros procesos" o posts de celebración con foto, sin
# necesitar un LLM.

SENAL_CONTRATACION = [
    "estamos buscando", "buscamos", "hiring", "we are hiring", "we're hiring",
    "vacante", "open position", "busqueda activa", "oportunidad laboral",
    "looking for a", "se busca", "join our team", "nueva busqueda",
]

SENAL_APLICACION = [
    "envia tu cv", "envianos tu cv", "postula", "aplica", "apply",
    "comparte tu cv", "send your resume", "send your cv", "hoja de vida",
    "link en comentarios", "dm me", "escribeme",
]

CORE = {  # +3 cada una
    "react": 3, "next.js": 3, "nextjs": 3, "typescript": 3,
    "frontend": 3, "front-end": 3, "front end": 3, "vtex": 3,
}

SECUNDARIO = {  # +1 cada una
    "javascript": 1, "node": 1, "graphql": 1, "tailwind": 1,
    "e-commerce": 1, "ecommerce": 1, "remoto": 1, "remote": 1,
    "latam": 1, "jest": 1, "redux": 1, "seo": 1, "lighthouse": 1,
}

VETO = [  # descartan el post
    "nestjs", "nest.js", "kubernetes", "kafka", "rabbitmq", "terraform",
    "php", "laravel", ".net", "dotnet", "react native", "flutter",
    "angular",  # solo si NO menciona react (se maneja abajo)
    "java developer", "spring boot", "python developer", "golang",
    "ingles avanzado", "advanced english", "fluent english", "english c1",
    "excellent english", "ingles fluido",
]

UMBRAL_REVISAR = 4
UMBRAL_TALVEZ = 1


def normalizar(texto: str) -> str:
    """Convierte unicode estilizado (𝐒𝐨𝐟𝐭𝐰𝐚𝐫𝐞→Software), minúsculas, sin tildes."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower()


def es_vacante(texto: str) -> bool:
    """Requiere señal de contratación + señal de aplicación/contacto."""
    tiene_contratacion = any(s in texto for s in SENAL_CONTRATACION)
    tiene_aplicacion = (
        any(s in texto for s in SENAL_APLICACION)
        or re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", texto)
        or "lnkd.in" in texto
    )
    return tiene_contratacion and bool(tiene_aplicacion)


def calcular_score(texto: str):
    """Devuelve (score, vetos_encontrados)."""
    score = 0
    for kw, peso in CORE.items():
        if kw in texto:
            score += peso
    for kw, peso in SECUNDARIO.items():
        if kw in texto:
            score += peso

    vetos = [v for v in VETO if v in texto]
    # excepción: "angular" no veta si también piden react (React OR Angular)
    if "angular" in vetos and "react" in texto:
        vetos.remove("angular")
    return score, vetos


def extraer_contacto(texto_original: str):
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", texto_original)
    links = re.findall(r"https?://\S+|lnkd\.in/\S+", texto_original)
    return emails, links


def clasificar_post_feed(descripcion: str) -> dict | None:
    """
    Punto de entrada único para normalizar_vacante: aplica todo el algoritmo
    (normalización, "¿es vacante?", score de stack + veto, extracción de
    contacto) y retorna None si se descarta, o un dict con decision
    (REVISAR/TAL_VEZ), score, emails y links si sobrevive. La deduplicación
    entre archivos de scraping distintos la hace pipeline.py, que es quien
    itera sobre ellos.
    """
    texto = normalizar(descripcion)
    if not es_vacante(texto):
        return None

    score, vetos = calcular_score(texto)
    if vetos or score < UMBRAL_TALVEZ:
        return None

    emails, links = extraer_contacto(descripcion)
    decision = "REVISAR" if score >= UMBRAL_REVISAR else "TAL_VEZ"

    return {
        "decision": decision,
        "score": score,
        "emails": emails,
        "links": links[:3],
    }
