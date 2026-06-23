import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_ENABLED = bool(API_KEY and API_KEY != "your_gemini_api_key_here")

if GEMINI_ENABLED:
    genai.configure(api_key=API_KEY)


def filtrar_con_gemini(vacante: dict, perfil: dict) -> dict:
    """
    Envía vacante + perfil a Gemini.
    Retorna: { pasa: bool, razon: str }
    Solo llamar si score > 50 (ahorra tokens del free tier).
    """
    if not GEMINI_ENABLED:
        return {"pasa": True, "razon": "GEMINI_API_KEY no configurada — skipped"}

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
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Limpiar posibles backticks
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)

        return {
            "pasa": bool(result.get("pasa", False)),
            "razon": result.get("razon", ""),
        }

    except json.JSONDecodeError:
        return {"pasa": False, "razon": f"Error parsing Gemini response: {text[:100]}"}
    except Exception as e:
        return {"pasa": False, "razon": f"Error Gemini API: {str(e)}"}
