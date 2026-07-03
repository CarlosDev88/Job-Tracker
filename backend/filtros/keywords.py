import json
import re

STACK_CORE = {
    "react", "typescript", "next.js", "nextjs", "javascript",
    "frontend", "front-end", "front end", "tailwind",
}

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
    "wordpress": -150,
    "drupal": -150,
    "django": -80,
    "odoo": -80,
    "salesforce": -80,
    "cobol": -200,
    "ruby on rails": -60,
    "golang": -40,
}

BLACKLIST_PATTERNS = [
    r"\bspring boot\b",
    r"\bspring framework\b",
    r"\basp\.net\b",
    r"\bc#\b",
    r"\bwordpress\b",
    r"\bdrupal\b",
    r"\bjoomla\b",
    r"\bodoo\b",
    r"\bcobol\b",
    r"\bsalesforce\b(?!.*react)",  # salesforce OK si también menciona react
]

# Marcadores para distinguir "menciona" vs "requiere como core" (ver clasificar_requisito en spec.md)
DURO_HEADERS = [
    r"\bindispensable\b", r"\bexcluyente\b", r"\bmust have\b", r"\bfundamental\b",
    r"\bs[oó]lido\b", r"\bdominio\b", r"\bexperiencia s[oó]lida\b",
    r"\brequisitos\b", r"\brequerimientos\b", r"\bobligatorio\b",
]
BLANDO_HEADERS = [
    r"\bdeseable\b", r"\bnice to have\b", r"\bplus\b", r"\bvalorar[aá]\b",
    r"\bfamiliaridad\b", r"\bconocimiento b[aá]sico\b", r"\bopcional\b", r"\bbonus\b",
]

# Stacks que no dominamos: peso del gap si aparecen como requisito DURO.
# Umbral de descarte = suma de pesos de gaps_duros >= UMBRAL_GAPS_DUROS
STACK_AUSENTE_PESO = {
    "nestjs": 3,
    "kubernetes": 2,
    "kafka": 2,
    "terraform": 2,
    "supabase": 3,
    "php": 3,
    "java backend": 3,
    "python backend": 3,
    "react native producción": 3,
    "azure ad/entra": 1,
}

GAP_PATTERNS = {
    "nestjs": r"\bnest\.?js\b",
    "kubernetes": r"\bkubernetes\b|\bk8s\b",
    "kafka": r"\bkafka\b",
    "terraform": r"\bterraform\b",
    "supabase": r"\bsupabase\b",
    "php": r"\bphp\b(?!\s*:\s*\d)",  # php pero no "PHP: 7.4" como versión rara
    "java backend": r"\bjava\b(?![\s,;/]*script)",  # java pero NO javascript
    "python backend": r"\bpython\b",
    "react native producción": r"\breact native\b",
    "azure ad/entra": r"\bazure ad\b|\bentra id\b",
}

UMBRAL_GAPS_DUROS = 3
UMBRAL_SCORE_MIN = 20


def normalize(text: str) -> str:
    return text.lower().strip()


def blacklist_check(titulo: str, descripcion: str) -> bool:
    """Retorna True si debe ser descartada inmediatamente."""
    text = normalize(f"{titulo} {descripcion}")
    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def _mapa_zonas(text: str) -> list:
    """Ubica los headers DURO/BLANDO en el texto, en orden de aparición."""
    marcadores = []
    for pat in DURO_HEADERS:
        for m in re.finditer(pat, text):
            marcadores.append((m.start(), "DURO"))
    for pat in BLANDO_HEADERS:
        for m in re.finditer(pat, text):
            marcadores.append((m.start(), "BLANDO"))
    marcadores.sort(key=lambda x: x[0])
    return marcadores


def _zona_en(pos: int, marcadores: list) -> str:
    """Zona vigente en esa posición: el último header visto antes de pos, o DURO por defecto."""
    zona = "DURO"
    for marker_pos, marker_zona in marcadores:
        if marker_pos <= pos:
            zona = marker_zona
        else:
            break
    return zona


def _tiene_anios_experiencia_cerca(text: str, pos: int, ventana: int = 60) -> bool:
    inicio = max(0, pos - ventana)
    fin = min(len(text), pos + ventana)
    return bool(re.search(r"\d+\+?\s*años?", text[inicio:fin]))


def calcular_gaps(text: str, marcadores: list) -> dict:
    """
    Evalúa STACK_AUSENTE_PESO contra el texto, clasificando cada gap como
    DURO o BLANDO según la zona donde aparece (ver _mapa_zonas/_zona_en).
    Un "X+ años de experiencia" cerca del gap agrava su peso (+2).
    """
    gaps_duros = []
    gaps_blandos = []

    for keyword, pattern in GAP_PATTERNS.items():
        matches = list(re.finditer(pattern, text))

        if keyword == "react native producción" and matches:
            if not re.search(r"producci[oó]n", text):
                matches = []

        if not matches:
            continue

        es_duro = any(_zona_en(m.start(), marcadores) == "DURO" for m in matches)
        peso = STACK_AUSENTE_PESO[keyword]

        if es_duro and _tiene_anios_experiencia_cerca(text, matches[0].start()):
            peso += 2

        gap_info = {"keyword": keyword, "peso": peso}
        (gaps_duros if es_duro else gaps_blandos).append(gap_info)

    return {"gaps_duros": gaps_duros, "gaps_blandos": gaps_blandos}


def clasificar_ingles(text: str, ubicacion: str) -> str:
    """Retorna 'ALTO_DESCARTE', 'MEDIO', 'ALTO' o 'BAJO'."""
    contexto = normalize(f"{text} {ubicacion}")
    nivel_avanzado = bool(
        re.search(r"ingl[eé]s\s+(avanzado|fluido|advanced|fluent|excelente|excellent)", contexto)
    )
    if not nivel_avanzado:
        return "BAJO"

    remoto_us_eu = bool(re.search(r"\bremot[oa]\b|\bremote\b", contexto)) and bool(
        re.search(r"\b(usa|us|united states|europa|europe)\b", contexto)
    )
    latam_interno = bool(
        re.search(r"\blatam\b|\bcolombia\b|\bméxico\b|\bmexico\b|\bargentina\b|\bchile\b|\bperú\b|\bperu\b", contexto)
    )

    if remoto_us_eu and not latam_interno:
        return "ALTO_DESCARTE"
    if latam_interno:
        return "MEDIO"
    return "ALTO"


def calcular_score(titulo: str, descripcion: str, perfil: dict) -> dict:
    text = normalize(f"{titulo} {descripcion}")

    score = 0
    matches_positivos = []
    matches_negativos = []

    nestjs_presente = bool(re.search(GAP_PATTERNS["nestjs"], text))

    for keyword, weight in WEIGHTS.items():
        # "el más restrictivo gana": NestJS es la señal real, no el Node.js genérico
        if keyword in ("node.js", "nodejs") and nestjs_presente:
            continue

        pattern = rf"\b{re.escape(keyword)}\b"
        if re.search(pattern, text):
            score += weight
            (matches_positivos if weight > 0 else matches_negativos).append(
                {"keyword": keyword, "peso": weight}
            )

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

    marcadores = _mapa_zonas(text)
    gaps = calcular_gaps(text, marcadores)

    return {
        "score": max(0, min(100, score)),
        "score_raw": score,
        "positivos": matches_positivos,
        "negativos": matches_negativos,
        "gaps_duros": gaps["gaps_duros"],
        "gaps_blandos": gaps["gaps_blandos"],
    }


def filtrar_vacante(vacante: dict, perfil: dict) -> dict:
    titulo = vacante.get("titulo", "")
    descripcion = vacante.get("descripcion", "")
    ubicacion = vacante.get("ubicacion", "")

    if blacklist_check(titulo, descripcion):
        return {
            "pasa": False,
            "razon": "blacklist",
            "score": 0,
            "detalle": {"decision": "NO_APLICAR", "razon_descarte": "stack incompatible"},
        }

    resultado = calcular_score(titulo, descripcion, perfil)
    riesgo_ingles = clasificar_ingles(f"{titulo} {descripcion}", ubicacion)
    resultado["riesgo_ingles"] = "ALTO" if riesgo_ingles == "ALTO_DESCARTE" else riesgo_ingles

    if riesgo_ingles == "ALTO_DESCARTE":
        return {
            "pasa": False,
            "razon": "ingles_estricto",
            "score": resultado["score"],
            "detalle": {
                **resultado,
                "decision": "NO_APLICAR",
                "razon_descarte": "inglés avanzado/fluido exigido para remoto US/Europa",
            },
        }

    peso_gaps_duros = sum(g["peso"] for g in resultado["gaps_duros"])
    if peso_gaps_duros >= UMBRAL_GAPS_DUROS:
        gaps_nombres = ", ".join(g["keyword"] for g in resultado["gaps_duros"])
        return {
            "pasa": False,
            "razon": "gaps_duros",
            "score": resultado["score"],
            "detalle": {
                **resultado,
                "decision": "NO_APLICAR",
                "razon_descarte": f"gaps duros acumulados ({peso_gaps_duros}): {gaps_nombres}",
            },
        }

    if resultado["score"] < UMBRAL_SCORE_MIN:
        return {
            "pasa": False,
            "razon": "score_bajo",
            "score": resultado["score"],
            "detalle": {**resultado, "decision": "NO_APLICAR"},
        }

    tiene_reservas = bool(resultado["gaps_blandos"]) or riesgo_ingles == "MEDIO"
    decision = "APLICAR_CON_RESERVA" if tiene_reservas else "APLICAR"

    return {
        "pasa": True,
        "razon": "ok",
        "score": resultado["score"],
        "detalle": {**resultado, "decision": decision},
    }
