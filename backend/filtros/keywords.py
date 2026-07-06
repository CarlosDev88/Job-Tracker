import json
import re
import unicodedata

# Hard blacklist: stacks tan incompatibles con un perfil React/Next.js que
# mencionarlos en cualquier parte (incluso en la sección deseable) descarta —
# a diferencia de VETO_DURO_PATTERNS de abajo, que solo veta si aparece en la
# sección de requisitos duros.
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

DURO_HEADERS = [
    r"\bindispensable\b", r"\bexcluyente\b", r"\bmust have\b", r"\bfundamental\b",
    r"\bs[oó]lido\b", r"\bdominio\b", r"\bexperiencia s[oó]lida\b",
    r"\brequisitos\b", r"\brequerimientos\b", r"\bobligatorio\b",
    r"\brequirements?\b", r"\bwhat you bring\b", r"\bqu[eé] debes tener\b",
]
BLANDO_HEADERS = [
    r"\bdeseable\b", r"\bnice to have\b", r"\bplus\b", r"\bvalorar[aá]\b",
    r"\bfamiliaridad\b", r"\bconocimiento b[aá]sico\b", r"\bopcional(es)?\b", r"\bbonus\b",
    r"\bbeneficios\b", r"\bcondiciones\b", r"\bbenefits\b",
]

# Stack incompatible, pero contextual: solo descarta si aparece en la sección
# de requisitos duros (ver _mapa_zonas/_zona_en). En la sección deseable queda
# como "gap blando" informativo, no descarta.
VETO_DURO_PATTERNS = {
    "nestjs": r"\bnest\.?js\b",
    "kubernetes": r"\bkubernetes\b|\bk8s\b",
    "kafka": r"\bkafka\b",
    "rabbitmq": r"\brabbitmq\b",
    "terraform": r"\bterraform\b",
    "php": r"\bphp\b(?!\s*:\s*\d)",
    "laravel": r"\blaravel\b",
    ".net": r"\bdotnet\b|\b\.net\b",
    "java backend": r"\bjava\b(?![\s,;/]*script)",
    "python backend": r"\bpython\b",
    "react native": r"\breact native\b",
    "angular": r"\bangular\b",  # excepción: no veta si también piden react
    "supabase": r"\bsupabase\b",
    "prisma": r"\bprisma\b",
    "shopify/liquid": r"\bshopify\b|\bliquid\b",
    "dynamodb/sqs/sns/eventbridge": r"\bdynamodb\b|\bsqs\b|\bsns\b|\beventbridge\b",
}

VETO_IDIOMA = re.compile(
    r"ingl[eé]s\s+(avanzado|fluido|advanced|fluent|excelente|excellent)|\bc1\b",
    re.IGNORECASE,
)

# Perfil: Senior Frontend React/Next.js/TS/VTEX, base en Bucaramanga.
CORE = ["react", "next.js", "nextjs", "typescript", "frontend", "front-end", "front end", "vtex"]
SECUNDARIO = ["node", "node.js", "nodejs", "graphql", "aws", "jest", "redux", "tailwind", "seo", "core web vitals", "cwv"]
BONUS_PERFIL = ["e-commerce", "ecommerce", "retail", "performance", "lighthouse", "i18n"]

UMBRAL_APLICAR_YA = 55
UMBRAL_APLICAR = 35
UMBRAL_REVISAR_MANUAL = 20


def normalize(text: str) -> str:
    """NFKD + sin tildes + minúsculas — crítico para Unicode estilizado (𝐒𝐨𝐟𝐭𝐰𝐚𝐫𝐞→software)."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower().strip()


def blacklist_check(titulo: str, descripcion: str) -> bool:
    """Retorna True si debe ser descartada inmediatamente, sin importar la sección."""
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


def _veto_stack(texto: str, marcadores: list) -> tuple:
    """Evalúa VETO_DURO_PATTERNS: retorna (vetos_duros, vetos_blandos) según la zona donde aparecen."""
    duros, blandos = [], []
    for kw, pattern in VETO_DURO_PATTERNS.items():
        matches = list(re.finditer(pattern, texto))
        if not matches:
            continue
        if kw == "angular" and re.search(r"\breact\b", texto):
            continue  # react + angular no veta: react gana
        zona = _zona_en(matches[0].start(), marcadores)
        (duros if zona == "DURO" else blandos).append(kw)
    return duros, blandos


def _veto_idioma(texto: str) -> bool:
    return bool(VETO_IDIOMA.search(texto))


def _veto_ubicacion(ubicacion: str, texto: str) -> bool:
    """Presencial/híbrido fuera de Bucaramanga (y sin mención de remoto) descarta."""
    contexto = normalize(f"{ubicacion} {texto}")
    es_presencial_hibrido = bool(re.search(r"h[ií]brido|presencial|on-?site", contexto))
    if not es_presencial_hibrido:
        return False
    menciona_bucaramanga = "bucaramanga" in contexto
    menciona_remoto = bool(re.search(r"\bremot[oa]\b|\bremote\b", contexto))
    return not (menciona_bucaramanga or menciona_remoto)


def calcular_score(titulo: str, descripcion: str, perfil: dict) -> dict:
    """
    Score 0-100. El título pesa doble (+15/keyword CORE, tope 30) porque un
    puesto que dice "React" en el título es una señal más fuerte que uno que
    lo menciona de pasada en el cuerpo (+8, y solo si cae en la sección de
    requisitos duros). Secundarios y bonus de perfil no dependen de sección.
    """
    titulo_n = normalize(titulo)
    desc_n = normalize(descripcion)
    texto = f"{titulo_n} {desc_n}"
    marcadores = _mapa_zonas(desc_n)

    score = 0
    positivos = []
    negativos = []

    title_bonus = 0
    for kw in CORE:
        if re.search(rf"\b{re.escape(kw)}\b", titulo_n):
            positivos.append({"keyword": kw, "peso": 15, "zona": "titulo"})
            title_bonus += 15
    score += min(title_bonus, 30)

    for kw in CORE:
        for m in re.finditer(rf"\b{re.escape(kw)}\b", desc_n):
            if _zona_en(m.start(), marcadores) == "DURO":
                positivos.append({"keyword": kw, "peso": 8, "zona": "dura"})
                score += 8
                break

    for kw in SECUNDARIO:
        if re.search(rf"\b{re.escape(kw)}\b", texto):
            positivos.append({"keyword": kw, "peso": 3, "zona": "secundario"})
            score += 3

    for kw in BONUS_PERFIL:
        if re.search(rf"\b{re.escape(kw)}\b", texto):
            positivos.append({"keyword": kw, "peso": 5, "zona": "bonus"})
            score += 5

    # Perfil dinámico (tabla perfiles): keywords propias del usuario, encima del stack hardcodeado
    keywords_incluir = json.loads(perfil.get("keywords_incluir", "[]"))
    keywords_excluir = json.loads(perfil.get("keywords_excluir", "[]"))

    for kw in keywords_incluir:
        kw_n = normalize(kw)
        if kw_n and re.search(rf"\b{re.escape(kw_n)}\b", texto):
            positivos.append({"keyword": kw_n, "peso": 5, "fuente": "perfil"})
            score += 5

    for kw in keywords_excluir:
        kw_n = normalize(kw)
        if kw_n and re.search(rf"\b{re.escape(kw_n)}\b", texto):
            negativos.append({"keyword": kw_n, "peso": -30, "fuente": "perfil"})
            score -= 30

    anios = [int(n) for n in re.findall(r"\b(\d{1,2})\+?\s*a[ñn]os?\b", texto)]
    if anios:
        anio_max = max(anios)
        if 3 <= anio_max <= 4:
            positivos.append({"keyword": f"{anio_max}+ años (cumples)", "peso": 5})
            score += 5
        elif anio_max >= 6:
            negativos.append({"keyword": f"{anio_max}+ años (riesgo, tienes 5)", "peso": -10})
            score -= 10

    # Si el texto llegó hasta acá es porque ya pasó el veto de inglés avanzado/fluido/C1
    positivos.append({"keyword": "inglés no avanzado", "peso": 5})
    score += 5

    if re.search(r"\bremot[oa]\b|\bremote\b", texto) and re.search(r"\blatam\b|\bcolombia\b", texto):
        positivos.append({"keyword": "remoto latam/colombia", "peso": 5})
        score += 5

    return {
        "score": max(0, min(100, score)),
        "score_raw": score,
        "positivos": positivos,
        "negativos": negativos,
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

    texto = normalize(f"{titulo} {descripcion}")
    marcadores = _mapa_zonas(normalize(descripcion))

    if _veto_idioma(texto):
        return {
            "pasa": False,
            "razon": "ingles_estricto",
            "score": 0,
            "detalle": {"decision": "NO_APLICAR", "razon_descarte": "inglés avanzado/fluido/C1 exigido"},
        }

    if _veto_ubicacion(ubicacion, texto):
        return {
            "pasa": False,
            "razon": "ubicacion_incompatible",
            "score": 0,
            "detalle": {"decision": "NO_APLICAR", "razon_descarte": "presencial/híbrido fuera de Bucaramanga"},
        }

    vetos_duros, vetos_blandos = _veto_stack(texto, marcadores)
    if vetos_duros:
        return {
            "pasa": False,
            "razon": "veto_stack",
            "score": 0,
            "detalle": {
                "decision": "NO_APLICAR",
                "razon_descarte": f"stack incompatible en requisitos duros: {', '.join(vetos_duros)}",
                "gaps_duros": [{"keyword": k} for k in vetos_duros],
            },
        }

    resultado = calcular_score(titulo, descripcion, perfil)
    score = resultado["score"]

    if score >= UMBRAL_APLICAR_YA:
        decision = "APLICAR_YA"
    elif score >= UMBRAL_APLICAR:
        decision = "APLICAR"
    elif score >= UMBRAL_REVISAR_MANUAL:
        decision = "REVISAR_MANUAL"
    else:
        return {
            "pasa": False,
            "razon": "score_bajo",
            "score": score,
            "detalle": {**resultado, "decision": "NO_APLICAR"},
        }

    return {
        "pasa": True,
        "razon": "ok",
        "score": score,
        "detalle": {
            **resultado,
            "gaps_duros": [],
            "gaps_blandos": [{"keyword": k} for k in vetos_blandos],
            "riesgo_ingles": "BAJO",
            "decision": decision,
        },
    }
