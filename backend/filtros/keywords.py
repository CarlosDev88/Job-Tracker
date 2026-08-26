import json
import re

from backend.filtros.texto import contiene, normalizar_texto

BLACKLIST_PATTERNS = {
    "spring": r"\bspring (boot|framework)\b",
    "asp.net": r"(?<!\w)asp\.net(?!\w)",
    "c#": r"(?<!\w)c#(?!\w)",
    "wordpress": r"\bwordpress\b",
    "drupal": r"\bdrupal\b",
    "joomla": r"\bjoomla\b",
    "odoo": r"\bodoo\b",
    "cobol": r"\bcobol\b",
}

DURO_HEADERS = [
    r"\bindispensable\b", r"\bexcluyente\b", r"\bmust have\b",
    r"\bfundamental\b", r"\bs[oó]lido\b", r"\bdominio\b",
    r"\bexperiencia s[oó]lida\b", r"\brequisitos\b",
    r"\brequerimientos\b", r"\bobligatorio\b", r"\brequirements?\b",
    r"\bwhat you bring\b", r"\bqu[eé] debes tener\b",
]
BLANDO_HEADERS = [
    r"\bdeseable\b", r"\bnice to have\b", r"\bplus\b",
    r"\bvalorar[aá]\b", r"\bfamiliaridad\b", r"\bconocimiento b[aá]sico\b",
    r"\bopcional(es)?\b", r"\bbonus\b", r"\bbeneficios\b",
    r"\bcondiciones\b", r"\bbenefits\b",
]

VETOS = {
    "nestjs": r"(?<!\w)nest\.?js(?!\w)",
    "kubernetes": r"\b(kubernetes|k8s)\b",
    "kafka": r"\bkafka\b",
    "rabbitmq": r"\brabbitmq\b",
    "terraform": r"\bterraform\b",
    "php": r"\bphp\b(?!\s*:\s*\d)",
    "laravel": r"\blaravel\b",
    ".net": r"(?<!\w)(dotnet|\.net)(?!\w)",
    "java backend": r"\bjava\b(?![\s,;/]*script)",
    "python backend": r"\bpython\b",
    "react native": r"\breact native\b",
    "angular": r"\bangular\b",
    "supabase": r"\bsupabase\b",
    "prisma": r"\bprisma\b",
    "shopify/liquid": r"\b(shopify|liquid)\b",
    "dynamodb/sqs/sns/eventbridge": r"\b(dynamodb|sqs|sns|eventbridge)\b",
}

CORE_GRUPOS = {
    "react": ["react", "react.js", "reactjs"],
    "next": ["next.js", "nextjs"],
    "typescript": ["typescript"],
    "frontend": ["frontend", "front-end", "front end"],
    "vtex": ["vtex"],
}
SECUNDARIO_GRUPOS = {
    "node": ["node", "node.js", "nodejs"],
    "graphql": ["graphql"],
    "aws": ["aws"],
    "jest": ["jest"],
    "redux": ["redux"],
    "tailwind": ["tailwind"],
    "seo": ["seo"],
    "core web vitals": ["core web vitals", "cwv"],
}
BONUS_GRUPOS = {
    "e-commerce": ["e-commerce", "ecommerce"],
    "retail": ["retail"],
    "performance": ["performance"],
    "lighthouse": ["lighthouse"],
    "i18n": ["i18n"],
}

UMBRAL_APLICAR_YA = 55
UMBRAL_APLICAR = 35
UMBRAL_REVISAR_MANUAL = 20


def _zonas(descripcion: str) -> list[tuple[int, int, str]]:
    marcadores = []
    for patron in DURO_HEADERS:
        marcadores.extend((match.start(), "DURO") for match in re.finditer(patron, descripcion))
    for patron in BLANDO_HEADERS:
        marcadores.extend((match.start(), "BLANDO") for match in re.finditer(patron, descripcion))
    marcadores.sort()

    zonas, inicio, tipo = [], 0, "DURO"
    for posicion, nuevo_tipo in marcadores:
        if posicion > inicio:
            zonas.append((inicio, posicion, tipo))
        inicio, tipo = posicion, nuevo_tipo
    zonas.append((inicio, len(descripcion), tipo))
    return zonas


def _tipo_zona(posicion: int, zonas: list[tuple[int, int, str]]) -> str:
    for inicio, fin, tipo in zonas:
        if inicio <= posicion < fin:
            return tipo
    return "DURO"


def _clasificar_patron(titulo: str, descripcion: str, patron: str) -> str:
    if re.search(patron, titulo):
        return "DURO"
    zonas = _zonas(descripcion)
    apariciones = list(re.finditer(patron, descripcion))
    if not apariciones:
        return "AUSENTE"
    tipos = {_tipo_zona(match.start(), zonas) for match in apariciones}
    return "DURO" if "DURO" in tipos else "BLANDO"


def _conceptos_presentes(texto: str, grupos: dict[str, list[str]]) -> set[str]:
    return {
        concepto
        for concepto, aliases in grupos.items()
        if any(contiene(texto, alias) for alias in aliases)
    }


def _lista_json(perfil: dict, campo: str) -> list[str]:
    try:
        value = perfil.get(campo, "[]")
        return value if isinstance(value, list) else json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []


def _ingles_avanzado(texto: str) -> bool:
    return bool(re.search(
        r"(ingl[eé]s|english)\s+(avanzado|fluido|advanced|fluent|excelente|excellent)"
        r"|\b(c1|c2)\b.{0,30}\b(ingl[eé]s|english)\b"
        r"|\b(ingl[eé]s|english)\b.{0,30}\b(c1|c2)\b",
        texto,
    ))


def _veto_ubicacion(ubicacion: str, texto: str, ubicacion_base: str) -> bool:
    contexto = f"{normalizar_texto(ubicacion)} {texto}"
    presencial = bool(re.search(r"h[ií]brido|presencial|on-?site", contexto))
    remoto = bool(re.search(r"\bremot[oa]\b|\bremote\b", contexto))
    return presencial and not remoto and normalizar_texto(ubicacion_base) not in contexto


def _detalle_base() -> dict:
    return {
        "positivos": [],
        "negativos": [],
        "gaps_duros": [],
        "gaps_blandos": [],
        "riesgo_ingles": "BAJO",
    }


def _ya_puntuado_por_core(keyword: str, puntuados: set[str]) -> bool:
    return any(
        keyword in {normalizar_texto(alias) for alias in CORE_GRUPOS[concepto]}
        for concepto in puntuados
    )


def calcular_score(titulo: str, descripcion: str, perfil: dict) -> dict:
    titulo_n = normalizar_texto(titulo)
    descripcion_n = normalizar_texto(descripcion)
    texto = f"{titulo_n} {descripcion_n}"
    detalle = _detalle_base()
    score = 0
    core_titulo = _conceptos_presentes(titulo_n, CORE_GRUPOS)
    score += min(30, 15 * len(core_titulo))
    for concepto in sorted(core_titulo):
        detalle["positivos"].append({"keyword": concepto, "peso": 15, "zona": "titulo"})

    zonas = _zonas(descripcion_n)
    puntuados = set(core_titulo)
    for concepto, aliases in CORE_GRUPOS.items():
        if concepto in puntuados:
            continue
        if any(
            _clasificar_patron("", descripcion_n, r"(?<!\w)" + re.escape(alias) + r"(?!\w)") == "DURO"
            for alias in aliases
        ):
            score += 8
            puntuados.add(concepto)
            detalle["positivos"].append({"keyword": concepto, "peso": 8, "zona": "dura"})

    for grupos, peso, zona in ((SECUNDARIO_GRUPOS, 3, "secundario"), (BONUS_GRUPOS, 5, "bonus")):
        for concepto in sorted(_conceptos_presentes(texto, grupos)):
            score += peso
            detalle["positivos"].append({"keyword": concepto, "peso": peso, "zona": zona})

    for keyword in _lista_json(perfil, "keywords_incluir"):
        keyword_n = normalizar_texto(keyword)
        if keyword_n and not _ya_puntuado_por_core(keyword_n, puntuados) and contiene(texto, keyword_n):
            score += 5
            detalle["positivos"].append({"keyword": keyword_n, "peso": 5, "zona": "perfil"})

    for keyword in _lista_json(perfil, "keywords_excluir"):
        keyword_n = normalizar_texto(keyword)
        patron = r"(?<!\w)" + re.escape(keyword_n) + r"(?!\w)"
        if keyword_n and _clasificar_patron(titulo_n, descripcion_n, patron) == "DURO":
            score -= 30
            detalle["negativos"].append({"keyword": keyword_n, "peso": -30, "zona": "perfil"})

    anios = [int(numero) for numero in re.findall(r"\b(\d{1,2})\+?\s*a[ñn]os?\b", texto)]
    if anios:
        mayor = max(anios)
        if 3 <= mayor <= 4:
            score += 5
            detalle["positivos"].append({"keyword": f"{mayor}+ años", "peso": 5})
        elif mayor >= 6:
            score -= 10
            detalle["negativos"].append({"keyword": f"{mayor}+ años", "peso": -10})

    score += 5
    detalle["positivos"].append({"keyword": "inglés no avanzado", "peso": 5})
    if re.search(r"\bremot[oa]\b|\bremote\b", texto) and re.search(r"\blatam\b|\bcolombia\b", texto):
        score += 5
        detalle["positivos"].append({"keyword": "remoto latam/colombia", "peso": 5})

    detalle["score_raw"] = score
    detalle["score"] = max(0, min(100, score))
    return detalle


def filtrar_vacante(vacante: dict, perfil: dict) -> dict:
    titulo = vacante.get("titulo", "")
    descripcion = vacante.get("descripcion", "")
    ubicacion = vacante.get("ubicacion", "")
    texto = normalizar_texto(f"{titulo} {descripcion}")

    for nombre, patron in BLACKLIST_PATTERNS.items():
        if re.search(patron, texto):
            return {"pasa": False, "razon": "blacklist", "score": 0, "detalle": {"decision": "NO_APLICAR", "razon_descarte": nombre}}

    if _ingles_avanzado(texto):
        return {"pasa": False, "razon": "ingles_estricto", "score": 0, "detalle": {"decision": "NO_APLICAR", "razon_descarte": "inglés avanzado exigido"}}

    if _veto_ubicacion(ubicacion, texto, perfil.get("ubicacion_base", "Bucaramanga")):
        return {"pasa": False, "razon": "ubicacion_incompatible", "score": 0, "detalle": {"decision": "NO_APLICAR", "razon_descarte": "presencial/híbrido fuera de Bucaramanga"}}

    titulo_n, descripcion_n = normalizar_texto(titulo), normalizar_texto(descripcion)
    duros, blandos = [], []
    for nombre, patron in VETOS.items():
        if nombre == "angular" and contiene(texto, "react"):
            continue
        tipo = _clasificar_patron(titulo_n, descripcion_n, patron)
        if tipo == "DURO":
            duros.append(nombre)
        elif tipo == "BLANDO":
            blandos.append(nombre)

    if duros:
        return {
            "pasa": False,
            "razon": "veto_stack",
            "score": 0,
            "detalle": {"decision": "NO_APLICAR", "gaps_duros": [{"keyword": item} for item in duros]},
        }

    detalle = calcular_score(titulo, descripcion, perfil)
    detalle["gaps_blandos"] = [{"keyword": item} for item in blandos]
    score = detalle["score"]
    if score >= UMBRAL_APLICAR_YA:
        decision = "APLICAR_YA"
    elif score >= UMBRAL_APLICAR:
        decision = "APLICAR"
    elif score >= UMBRAL_REVISAR_MANUAL:
        decision = "REVISAR_MANUAL"
    else:
        detalle["decision"] = "NO_APLICAR"
        return {"pasa": False, "razon": "score_bajo", "score": score, "detalle": detalle}

    detalle["decision"] = decision
    return {"pasa": True, "razon": "ok", "score": score, "detalle": detalle}
