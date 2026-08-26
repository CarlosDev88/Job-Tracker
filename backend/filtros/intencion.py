import re

from backend.filtros.texto import normalizar_texto

# Distingue quién habla y hacia dónde apunta la búsqueda, no el vocabulario
# técnico (un candidato de React describe su propio stack igual que una
# oferta real). Cada patrón suma 1 al conteo de su categoría; los regex de
# "looking for / buscando" pesan más porque desambiguan el caso más común
# (candidato "busco una oportunidad" vs. oferta "buscamos un desarrollador").

PATRONES_OFERTA = [
    r"\bestamos buscando\b", r"\bbuscamos (a )?(un|una)\b", r"\bse busca\b",
    r"\bwe(’|'| )?re hiring\b", r"\bwe are hiring\b", r"\bhiring a\b", r"\bis hiring\b",
    r"\bjoin our team\b", r"\bunete a nuestro equipo\b", r"\babrimos vacante\b",
    r"\bnueva vacante\b", r"\bvacante disponible\b", r"\bvacante para\b",
    r"\benvia tu cv a\b", r"\benvianos tu cv\b", r"\bpostulate\b", r"\bpostula aqui\b",
    r"\bapply now\b", r"\bapply here\b", r"\bfor our client\b", r"\bpara nuestro cliente\b",
    r"\blooking for (a|an) [a-z\s]{0,25}(developer|engineer|designer|programador|desarrollador)\b",
    r"\b(we|our (team|company|client)) (are |is )?(hiring|looking for)\b",
]

PATRONES_CANDIDATO = [
    r"#?opentowork", r"\bopen to work\b",
    r"\bestoy buscando (trabajo|empleo|oportunidad)\b",
    r"\bbusco (trabajo|empleo|nueva oportunidad|oportunidad laboral)\b",
    r"\bdisponible para nuevas oportunidades\b", r"\ben busqueda activa de trabajo\b",
    r"\bmi (cv|hoja de vida|portafolio)\b", r"\bcontactame\b", r"\bdm me\b",
    r"\bescribeme (al|a)\b", r"\brecien (egresado|graduado)\b",
    r"\b(i'?m|im|estoy) (actively )?(looking for|buscando) (a |an |una |un )?(new )?"
    r"(opportunity|role|position|job|oportunidad|trabajo|empleo)\b",
]

PATRONES_RUIDO_SOCIAL = [
    r"\bfeliz cumpleanos\b", r"\bhappy birthday\b", r"\baniversario laboral\b",
    r"\bwork anniversary\b", r"\bestoy feliz de anunciar\b", r"\bexcited to announce\b",
    r"\bme uno a\b", r"\b(i'?m|im) joining\b", r"\bfelicidades a\b", r"\bcongratulations to\b",
    r"\borgulloso de compartir\b", r"\bproud to share\b", r"\bnuevo puesto en\b",
    r"\bnuevo cargo en\b", r"\bcelebrando\b", r"\bcelebrating\b",
]


def _contar(texto: str, patrones: list[str]) -> int:
    return sum(1 for patron in patrones if re.search(patron, texto))


def detectar_intencion(titulo: str, descripcion: str) -> str:
    """Clasifica un post de LinkedIn como OFERTA (alguien busca candidato),
    CANDIDATO (alguien se ofrece), RUIDO_SOCIAL (cumpleaños, aniversarios,
    anuncios) o INDETERMINADO (ninguna señal clara, o señales empatadas)."""
    texto = normalizar_texto(f"{titulo} {descripcion}")

    puntajes = {
        "OFERTA": _contar(texto, PATRONES_OFERTA),
        "CANDIDATO": _contar(texto, PATRONES_CANDIDATO),
        "RUIDO_SOCIAL": _contar(texto, PATRONES_RUIDO_SOCIAL),
    }
    maximo = max(puntajes.values())
    if maximo == 0:
        return "INDETERMINADO"

    ganadores = [tipo for tipo, valor in puntajes.items() if valor == maximo]
    if len(ganadores) > 1:
        return "INDETERMINADO"
    return ganadores[0]
