import json
import re

WEIGHTS = {
    "react": 25,
    "typescript": 20,
    "next.js": 20,
    "nextjs": 20,
    "javascript": 15,
    "tailwind": 10,
    "vtex": 30,
    "node.js": 8,
    "nodejs": 8,
    "graphql": 8,
    "aws": 5,
    "storybook": 5,
    "module federation": 10,
    "micro frontend": 10,
    "microfrontend": 10,
    "zustand": 5,
    "redux": 5,
    "jest": 5,
    "testing library": 5,
    "remote": 5,
    "remoto": 5,
    "senior": 10,
    "frontend": 10,
    "front-end": 10,
    "front end": 10,
    "angular": -20,
    "vue": -15,
    "svelte": -10,
    "fullstack": -15,
    "full stack": -15,
    "full-stack": -15,
    "junior": -30,
    "entry level": -30,
    "intern": -50,
    "spring boot": -80,
    "spring framework": -80,
    ".net core": -100,
    "asp.net": -100,
    "c#": -100,
    "php": -100,
    "wordpress": -150,
    "drupal": -150,
    "django": -80,
    "odoo": -80,
    "salesforce": -80,
    "cobol": -200,
    "ruby on rails": -60,
    "golang": -40,
}

# "java" no debe matchear "javascript"
BLACKLIST_PATTERNS = [
    r"\bjava\b(?![\s,;/]*script)",  # java pero NO javascript
    r"\bspring boot\b",
    r"\bspring framework\b",
    r"\basp\.net\b",
    r"\bc#\b",
    r"\bphp\b(?!\s*:\s*\d)",  # php pero no "PHP: 7.4" como versión rara
    r"\bwordpress\b",
    r"\bdrupal\b",
    r"\bjoomla\b",
    r"\bodoo\b",
    r"\bcobol\b",
    r"\bsalesforce\b(?!.*react)",  # salesforce OK si también menciona react
]


def normalize(text: str) -> str:
    return text.lower().strip()


def blacklist_check(titulo: str, descripcion: str) -> bool:
    """Retorna True si debe ser descartada inmediatamente."""
    text = normalize(f"{titulo} {descripcion}")
    has_javascript = bool(re.search(r"\bjavascript\b", text))
    for pattern in BLACKLIST_PATTERNS:
        # Si el texto menciona javascript, ignorar el match de java
        if pattern.startswith(r"\bjava\b") and has_javascript:
            continue
        if re.search(pattern, text):
            return True
    return False


def calcular_score(titulo: str, descripcion: str, perfil: dict) -> dict:
    text = normalize(f"{titulo} {descripcion}")

    score = 0
    matches_positivos = []
    matches_negativos = []

    for keyword, weight in WEIGHTS.items():
        # Para "java" en WEIGHTS usar mismo patrón seguro
        if keyword == "java":
            pattern = r"\bjava\b(?![\s,;/]*script)"
        elif keyword == ".net":
            pattern = r"\.net\b"
        else:
            pattern = rf"\b{re.escape(keyword)}\b"

        if re.search(pattern, text):
            score += weight
            if weight > 0:
                matches_positivos.append({"keyword": keyword, "peso": weight})
            else:
                matches_negativos.append({"keyword": keyword, "peso": weight})

    keywords_incluir = json.loads(perfil.get("keywords_incluir", "[]"))
    keywords_excluir = json.loads(perfil.get("keywords_excluir", "[]"))

    for kw in keywords_incluir:
        kw_norm = normalize(kw)
        if kw_norm not in WEIGHTS and re.search(rf"\b{re.escape(kw_norm)}\b", text):
            score += 15
            matches_positivos.append(
                {"keyword": kw_norm, "peso": 15, "fuente": "perfil"}
            )

    for kw in keywords_excluir:
        kw_norm = normalize(kw)
        if kw_norm not in WEIGHTS and re.search(rf"\b{re.escape(kw_norm)}\b", text):
            score -= 50
            matches_negativos.append(
                {"keyword": kw_norm, "peso": -50, "fuente": "perfil"}
            )

    score_normalizado = max(0, min(100, score))

    return {
        "score": score_normalizado,
        "score_raw": score,
        "positivos": matches_positivos,
        "negativos": matches_negativos,
        "pasa": score_normalizado >= 20,
    }


def filtrar_vacante(vacante: dict, perfil: dict) -> dict:
    titulo = vacante.get("titulo", "")
    descripcion = vacante.get("descripcion", "")

    if blacklist_check(titulo, descripcion):
        return {"pasa": False, "razon": "blacklist", "score": 0, "detalle": {}}

    resultado = calcular_score(titulo, descripcion, perfil)

    return {
        "pasa": resultado["pasa"],
        "razon": "score_bajo" if not resultado["pasa"] else "ok",
        "score": resultado["score"],
        "detalle": resultado,
    }
