import json

from backend.llm.factory import get_connector


def filtrar_con_llm(vacante: dict, perfil: dict) -> dict:
    """
    Envía vacante + perfil al LLM configurado (ver LLM_PROVIDER en .env).
    Retorna: { pasa: bool, razon: str }
    Solo llamar si score > 50 (ahorra tokens/costos de API).
    """
    connector = get_connector()

    if not connector.enabled:
        return {"pasa": True, "razon": f"{connector.__class__.__name__} sin API key configurada — skipped"}

    prompt = f"""Eres un recruiter técnico senior. Analiza si esta vacante encaja con el perfil del candidato.

PERFIL DEL CANDIDATO:
{perfil.get('cv_texto', '')}

VACANTE:
Título: {vacante.get('titulo', '')}
Empresa: {vacante.get('empresa', '')}
Ubicación: {vacante.get('ubicacion', '')}
Descripción: {vacante.get('descripcion', '')[:2000]}

INSTRUCCIONES:
- Responde SOLO con JSON, sin markdown, sin explicaciones extra.
- Si el stack principal de la vacante es React/TypeScript/Next.js → pasa: true
- Si React es solo secundario y el core es otro stack → pasa: false
- Si el título dice Frontend pero la descripción pide Angular/Java/.NET como stack principal → pasa: false

Formato de respuesta EXACTO:
{{"pasa": true, "razon": "explicación breve en español de máximo 1 oración"}}
"""

    try:
        text = connector.generar(prompt)
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)

        return {
            "pasa": bool(result.get("pasa", False)),
            "razon": result.get("razon", ""),
        }

    except json.JSONDecodeError:
        return {"pasa": False, "razon": f"Error parsing respuesta LLM: {text[:100]}"}
    except Exception as e:
        return {"pasa": False, "razon": f"Error LLM: {str(e)}"}
