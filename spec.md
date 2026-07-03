# 1. MEJORA: distinguir "menciona" vs "requiere como core"
FUNCIÓN clasificar_requisito(texto_requisito, contexto_seccion):
    SI contexto_seccion EN ["indispensable", "excluyente", "must have", 
                            "fundamental", "sólido", "dominio", "experiencia sólida"]:
        RETORNAR "DURO"
    SI contexto_seccion EN ["deseable", "nice to have", "plus", "valorará",
                            "familiaridad", "conocimiento básico", "opcional"]:
        RETORNAR "BLANDO"
    # Regla default: si aparece en la sección de "Requerimientos/Requisitos" 
    # principal (no en "deseables"), tratar como DURO
    RETORNAR "DURO"

# 2. MEJORA: umbral de gaps duros, no solo lista binaria
STACK_AUSENTE_PESO = {
    "nestjs": 3,           # descarta solo, visto 8+ veces hoy
    "kubernetes": 2,
    "kafka": 2,
    "terraform": 2,
    "supabase": 3,
    "php": 3,
    "java backend": 3,
    "python backend": 3,
    "react native producción": 3,
    "azure ad/entra": 1,   # a veces opcional
}

SI suma_pesos(gaps_duros_encontrados) >= 3:
    RETORNAR "NO_APLICAR"

# 3. MEJORA: regla de "años de experiencia en X"
SI "X+ años" DURO Y X NOT IN STACK_CORE:
    # ej: "4+ años de experiencia con NestJS" es más grave 
    # que solo "conocimiento de NestJS"
    peso += 2

# 4. MEJORA: falsos positivos detectados hoy
# "Node.js" solo (sin framework específico) = OK, es tu BFF real
# "Node.js/NestJS" o "NestJS" solo = riesgo alto
SI "nestjs" IN texto Y "node.js" IN texto:
    tratar_como = "nestjs"  # el más restrictivo gana

# 5. MEJORA: inglés como filtro semi-duro, no solo riesgo
SI nivel_ingles == "advanced/fluent/excellent" Y modalidad == "remoto US/Europa":
    RETORNAR "NO_APLICAR"  # antes solo marcaba riesgo, hoy vimos que sí descarta
SINO SI nivel_ingles == "advanced" Y contexto == "LATAM interno":
    riesgo = "MEDIO"  # puede ser más flexible en la práctica

# 6. SALIDA para tu selección final
RETORNAR {
    "decision": "APLICAR" | "APLICAR_CON_RESERVA" | "NO_APLICAR",
    "gaps_duros": [...],
    "gaps_blandos": [...],
    "riesgo_ingles": "ALTO/MEDIO/BAJO",
    "score": 0.0-1.0,
    "razon_descarte": "..." (si aplica)
}