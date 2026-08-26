import re

from backend.filtros.texto import normalizar_texto

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
CORE = {"react": 3, "next.js": 3, "nextjs": 3, "typescript": 3, "frontend": 3, "front-end": 3, "front end": 3, "vtex": 3}
SECUNDARIO = {"javascript": 1, "node": 1, "graphql": 1, "tailwind": 1, "e-commerce": 1, "ecommerce": 1, "remoto": 1, "remote": 1, "latam": 1, "jest": 1, "redux": 1, "seo": 1, "lighthouse": 1}
VETO = ["nestjs", "nest.js", "kubernetes", "kafka", "rabbitmq", "terraform", "php", "laravel", ".net", "dotnet", "react native", "flutter", "angular", "java developer", "spring boot", "python developer", "golang", "ingles avanzado", "advanced english", "fluent english", "english c1", "excellent english", "ingles fluido"]
UMBRAL_REVISAR = 4
UMBRAL_TALVEZ = 1


def es_vacante(texto: str) -> bool:
    return any(senal in texto for senal in SENAL_CONTRATACION) and bool(
        any(senal in texto for senal in SENAL_APLICACION)
        or re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", texto)
        or "lnkd.in" in texto
    )


def extraer_contacto(texto: str) -> tuple[list[str], list[str]]:
    return (
        re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", texto),
        re.findall(r"https?://\S+|lnkd\.in/\S+", texto),
    )


def clasificar_post_feed(descripcion: str) -> dict | None:
    texto = normalizar_texto(descripcion)
    if not es_vacante(texto):
        return None

    vetos = [veto for veto in VETO if veto in texto]
    if "angular" in vetos and "react" in texto:
        vetos.remove("angular")
    if vetos:
        return None

    score = sum(peso for keyword, peso in CORE.items() if keyword in texto)
    score += sum(peso for keyword, peso in SECUNDARIO.items() if keyword in texto)
    if score < UMBRAL_TALVEZ:
        return None

    emails, links = extraer_contacto(descripcion)
    return {
        "decision": "REVISAR" if score >= UMBRAL_REVISAR else "TAL_VEZ",
        "score": score,
        "emails": emails,
        "links": links,
    }
