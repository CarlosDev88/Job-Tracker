FUNCIÓN filtrar_feed(posts, perfil):

    # 1. NORMALIZACIÓN (crítico por el Unicode estilizado)
    normalizar(texto):
        - unicodedata.normalize('NFKD')  # 𝐒𝐨𝐟𝐭𝐰𝐚𝐫𝐞 → Software
        - lowercase, quitar tildes

    # 2. DEDUPLICACIÓN
    hash = primeros_200_chars(descripcion)
    si hash ya visto → descartar

    # 3. ¿ES VACANTE? (2 señales mínimo, no 1)
    señal_contratacion = ["estamos buscando", "hiring", "vacante",
                          "open position", "we are hiring", "búsqueda activa"]
    señal_aplicacion   = ["envía tu cv", "postula", "aplica en", "@" + email,
                          "link en comentarios", "apply"]
    es_vacante = (≥1 de contratacion) Y (≥1 de aplicacion O tiene email O tiene link lnkd.in)
    # esto elimina falsos positivos tipo "buscamos mejorar nuestros procesos"

    # 4. MATCH DE STACK (tu perfil)
    CORE   = [react, next.js, typescript, frontend, vtex, javascript]  → +3 c/u
    SECUND = [node, graphql, tailwind, e-commerce, remoto latam]       → +1 c/u
    VETO   = [nestjs microservicios, kubernetes, php, java backend,
              react native, .net, angular only, inglés avanzado/c1]   → -5 c/u

    # 5. SCORE Y SALIDA
    score = suma_pesos
    SI score >= 4 Y sin_veto:   → "REVISAR" (guarda: autor, email extraído, link, score)
    SI score 1-3:               → "TAL_VEZ"
    SINO:                       → descartar

    # 6. EXTRAER DATOS DE CONTACTO
    email = regex(r'[\w.+-]+@[\w-]+\.[\w.]+')
    links = regex(r'lnkd\.in/\S+|https://\S+')

    RETORNAR ordenado_por_score(candidatas)



    #!/usr/bin/env python3
"""
Filtra posts del feed de LinkedIn (JSON del scraper) y detecta vacantes
que hacen match con el perfil: Senior Frontend (React/TS/Next.js/VTEX).

Uso:
    python filtrar_feed.py archivo1.json archivo2.json ...
Salida:
    - Imprime candidatas ordenadas por score
    - Genera vacantes_match.json con los resultados
"""

import json
import re
import sys
import unicodedata

# ----------------- CONFIGURACIÓN DEL PERFIL -----------------

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

# ----------------- FUNCIONES -----------------

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
        or re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", texto)  # email
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


def procesar(archivos):
    posts, vistos = [], set()
    for f in archivos:
        with open(f, encoding="utf-8") as fh:
            posts.extend(json.load(fh))

    resultados = []
    for p in posts:
        desc_orig = p.get("descripcion") or ""
        desc = normalizar(desc_orig)

        # dedupe por hash de los primeros 200 chars
        h = desc[:200]
        if h in vistos:
            continue
        vistos.add(h)

        if not es_vacante(desc):
            continue

        score, vetos = calcular_score(desc)
        if vetos or score < UMBRAL_TALVEZ:
            continue

        emails, links = extraer_contacto(desc_orig)
        resultados.append({
            "decision": "REVISAR" if score >= UMBRAL_REVISAR else "TAL_VEZ",
            "score": score,
            "autor": p.get("autor"),
            "autor_perfil": p.get("autor_perfil"),
            "emails": emails,
            "links": links[:3],
            "preview": desc_orig[:250].replace("\n", " "),
        })

    resultados.sort(key=lambda r: r["score"], reverse=True)
    return resultados


if __name__ == "__main__":
    archivos = sys.argv[1:]
    if not archivos:
        print("Uso: python filtrar_feed.py feed1.json feed2.json ...")
        sys.exit(1)

    res = procesar(archivos)
    for r in res:
        print(f"[{r['decision']} | score {r['score']}] {r['autor']}")
        if r["emails"]:
            print(f"   email: {', '.join(r['emails'])}")
        print(f"   {r['preview'][:150]}")
        print()

    with open("vacantes_match.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(f"Total candidatas: {len(res)} -> vacantes_match.json")