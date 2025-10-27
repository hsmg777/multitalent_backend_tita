# app/ext/ai_scorer.py
# -*- coding: utf-8 -*-
"""
AI Scorer: flujo de evaluación de postulantes basado en CV.
Incluye:
  - Envío básico a Chat Completions con control de reintentos
  - Scoring legacy (posición + skills)
  - Scoring v2 (perfiles + texto crudo del CV)
  - Flujo Pin-Pon:
      1) summarize_cv_to_json(): parsea el CV a JSON ESTRICTO (solo evidencia del PDF)
      2) score_candidate_v3(): compara JSON del CV vs perfil de vacante + perfil postulante (guías genéricas)

Buenas prácticas:
  - temperature=0 en parsing y scoring para reducir aleatoriedad
  - Prompts con "solo JSON" y "no inventes"
  - Limpieza y normalización de texto previo a parsing para mejorar comprensión
  - Sin hardcode de dominios, stacks, cargos o herramientas concretas
"""

import os
import re
import json
import time
import requests


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o")
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "100000"))  
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))



def _post_chat(
    messages,
    response_format="json_object",
    temperature=AI_TEMPERATURE,
    max_tokens=AI_MAX_TOKENS,
    retries=3,
    backoff=1.5,
):
    """
    Envía una conversación al endpoint /v1/chat/completions.
    - messages: [{"role":"system|user|assistant","content":"..."}]
    - response_format: "json_object" | "text"
    - control de reintentos exponenciales
    Devuelve SIEMPRE el "message.content" crudo (string). No recorta la respuesta.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY no configurado")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": AI_MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if response_format == "json_object":
        body["response_format"] = {"type": "json_object"}

    last_err = None
    for attempt in range(retries):
        try:
            r = requests.post(url, json=body, headers=headers, timeout=60)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
            time.sleep(backoff ** attempt)
    raise last_err


def _clamp(n, lo, hi):
    """Asegura score dentro de [lo, hi]. Si no es int, cae a 0."""
    try:
        n = int(n)
    except Exception:
        n = 0
    return max(lo, min(hi, n))



def _system_prompt_legacy() -> str:
    return (
        "Eres un evaluador técnico de RRHH. Analizas CVs para un puesto específico. "
        "Usa la rúbrica: experiencia (0..40), conocimientos (0..40), ajuste general (0..20). "
        "Devuelve SOLO JSON: {score:int 0..100, feedback:str 1–3 frases}."
    )


def _user_prompt_legacy(position, required_skills, nice_to_haves, min_years, applicant, cv_text) -> str:
    return f"""### CONTEXTO
- Puesto: {position}
- Requisitos obligatorios: {required_skills}
- Deseables: {nice_to_haves}
- Experiencia mínima requerida (años): {min_years}

### POSTULANTE (declarado)
{applicant}

### CV (texto completo)
{cv_text}

### INSTRUCCIONES
Evalúa con la rúbrica: experiencia (0..40), conocimientos (0..40), ajuste general (0..20).
Responde SOLO JSON:
{{
  "score": <entero 0..100>,
  "feedback": "<1 a 3 frases concisas>"
}}
"""


def score_candidate(position, required_skills, nice_to_haves, min_years, applicant, cv_text) -> dict:
    """
    Scoring clásico: compara una posición y listas de skills con texto crudo del CV.
    """
    messages = [
        {"role": "system", "content": _system_prompt_legacy()},
        {"role": "user", "content": _user_prompt_legacy(position, required_skills, nice_to_haves, min_years, applicant, cv_text)},
    ]
    raw = _post_chat(messages, response_format="json_object")
    try:
        obj = json.loads(raw)
    except Exception:
        obj = {"score": 0, "feedback": "Formato inválido (no-JSON)."}

    score = _clamp(obj.get("score"), 0, 100)
    feedback = (obj.get("feedback") or "").strip() or "Sin comentarios."
    return {"score": score, "feedback": feedback}



def _system_prompt_v2() -> str:
    return (
        "Eres un evaluador técnico de RRHH. Compara el perfil del postulante y su CV con el perfil del cargo. "
        "Rúbrica: experiencia (0..40), conocimientos (0..40), ajuste general (0..20). "
        "Devuelve SOLO JSON: {score:int 0..100, feedback:str 1–3 frases}."
    )


def _format_profile_block(title: str, data: dict) -> str:
    """
    Formatea perfiles (postulante o vacante) en bloques legibles para el LLM.
    """
    if "charge_title" in data:  
        fields = [
            ("Cargo", "charge_title"),
            ("Área", "charge_area"),
            ("Objetivo del rol", "role_objective"),
            ("Modalidad", "modality"),
            ("Ubicación", "location"),
            ("Responsabilidades", "responsibilities"),
            ("Requisitos (educación)", "req_education"),
            ("Requisitos (experiencia)", "req_experience"),
            ("Requisitos (conocimientos)", "req_knowledge"),
            ("Descripción del cargo", "charge_description"),
        ]
    else:  
        fields = [
            ("Residencia", "residence_addr"),
            ("Edad", "age"),
            ("Años en el rol", "role_exp_years"),
            ("Aspiración salarial", "expected_salary"),
            ("Identificación", "credential"),
            ("Teléfono", "phone"),
        ]
    lines = [f"[{title}]"]
    for label, key in fields:
        val = data.get(key)
        if val not in (None, "", [], {}):
            lines.append(f"- {label}: {val}")
    return "\n".join(lines)


def _comparison_prompt(applicant_profile: dict, vacancy_profile: dict, cv_text: str) -> str:
    return f"""
{_format_profile_block("PERFIL DEL POSTULANTE", applicant_profile)}

{_format_profile_block("PERFIL DEL CARGO", vacancy_profile)}

[INICIO CV - COMPLETO]
{cv_text}
[FIN CV - COMPLETO]
INSTRUCCIONES
1) Evalúa experiencia, conocimientos y ajuste general (educación/ubicación/modalidad).
2) Verifica consistencia entre perfil declarado y CV.
3) No penalices aspiración salarial salvo incompatibilidad evidente.
4) Devuelve SOLO JSON con:
{{
  "score": <entero 0..100>,
  "feedback": "<3 frases concisas>"
}}
"""


def score_candidate_v2(applicant_profile: dict, vacancy_profile: dict, cv_text: str) -> dict:
    """
    v2: compara perfiles contra texto crudo del CV (sin estructura).
    """
    messages = [
        {"role": "system", "content": _system_prompt_v2()},
        {"role": "user", "content": _comparison_prompt(applicant_profile, vacancy_profile, cv_text)},
    ]
    raw = _post_chat(messages, response_format="json_object")
    try:
        obj = json.loads(raw)
    except Exception:
        obj = {"score": 0, "feedback": "Formato inválido (no-JSON)."}

    score = _clamp(obj.get("score"), 0, 100)
    feedback = (obj.get("feedback") or "").strip() or "Sin comentarios."
    return {"score": score, "feedback": feedback}


# =======================================================
# Flujo Pin-Pon (Resumen → Scoring v3, genérico multi-industria)
# =======================================================

def _normalize_cv_text(cv_text: str) -> str:
    """
    Limpia y formatea el texto del CV para mejorar el parsing:
      - Colapsa espacios
      - Estabiliza saltos de línea
      - Marca secciones comunes como encabezados
      - Normaliza bullets
    (sin supuestos de dominio)
    """
    text = cv_text or ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(
        r"(?i)\b(HABILIDADES|COMPETENCIAS|SKILLS|EXPERIENCIA|EXPERIENCE|EDUCACION|EDUCATION|CERTIFICADOS|CERTIFICATIONS|IDIOMAS|LANGUAGES|RESUMEN|RESUME|SOBRE MI|ABOUT|PROYECTOS|PROJECTS|CONTACTO|REFERENCIAS)\b",
        r"\n### \1\n",
        text,
    )
    text = text.replace("•", "- ").replace("●", "- ").replace("·", "- ")
    return text.strip()


def _system_prompt_cv_parser() -> str:
    return (
        "Eres un estricto PARSER de currículums. Tu tarea es LEER el texto del CV y devolver "
        "UN JSON ESTRICTO con secciones estructuradas SOLO con información presente en el texto.\n"
        "PROHIBIDO inventar, inferir de contexto o agregar campos que no estén literal o inequívocamente presentes.\n"
        "Si algún campo no aparece, devuélvelo como null o [].\n"
        "Formato JSON:\n"
        "{\n"
        "  \"identidad\": { \"nombre\": null|string, \"email\": null|string, \"telefono\": null|string, \"ubicacion\": null|string },\n"
        "  \"educacion\": [ { \"titulo\": string, \"institucion\": string, \"periodo\": string|null } ],\n"
        "  \"experiencia\": [ { \"puesto\": string, \"empresa\": string|null, \"periodo\": string|null, \"funciones\": [string] } ],\n"
        "  \"habilidades\": [string],\n"
        "  \"certificaciones\": [ { \"nombre\": string, \"emisor\": string|null, \"url\": string|null } ],\n"
        "  \"idiomas\": [ { \"idioma\": string, \"nivel\": string|null } ],\n"
        "  \"links\": { \"linkedin\": string|null, \"github\": string|null }\n"
        "}\n"
        "Responde SOLO con JSON válido. No comentes."
    )


def _user_prompt_cv_parser(cv_text: str) -> str:
    return (
        "CV (TEXTO):\n"
        "----------------------------------------\n"
        f"{cv_text}\n"
        "----------------------------------------\n"
        "Devuelve el JSON solicitado. NO inventes."
    )


def summarize_cv_to_json(cv_text: str) -> dict:
    """
    Pin-Pon (Paso 1): Normaliza y parsea el CV a un JSON canónico con evidencia explícita.
    Nunca recorta la respuesta de la API antes de hacer json.loads.
    """
    normalized = _normalize_cv_text(cv_text)
    messages = [
        {"role": "system", "content": _system_prompt_cv_parser()},
        {"role": "user", "content": _user_prompt_cv_parser(normalized)},
    ]
    raw = _post_chat(messages, response_format="json_object", temperature=0.7, max_tokens=min(8000, AI_MAX_TOKENS))
    try:
        return json.loads(raw)
    except Exception:
        return {
            "identidad": {"nombre": None, "email": None, "telefono": None, "ubicacion": None},
            "educacion": [],
            "experiencia": [],
            "habilidades": [],
            "certificaciones": [],
            "idiomas": [],
            "links": {"linkedin": None, "github": None},
            "_raw": normalized,  
        }


def _canonicalize_terms(items: list[str]) -> list[str]:
    """
    Normalizador GENÉRICO (multi-industria, sin listas específicas):
      - separa etiquetas compuestas por delimitadores comunes
      - remueve espacios duplicados
      - mantiene el contenido textual original en minúsculas
    NO mapea ni asume equivalencias de dominio (no agrega términos nuevos).
    """
    if not items:
        return []
    out = []
    for raw in items:
        s = (raw or "").strip()
        if not s:
            continue
        parts = re.split(r"[,/|;()\[\]{}<>•·]+", s)
        for p in parts:
            p = p.strip().lower()
            if p:
                out.append(p)
    seen = set()
    result = []
    for x in out:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result


def _system_prompt_v3() -> str:
    return (
        "Eres un evaluador de RRHH para múltiples industrias. "
        "Usa el JSON estructurado del CV (sin inventar) para comparar contra el perfil de la vacante.\n"
        "Rúbrica: experiencia (0..40), conocimientos (0..40), ajuste general (0..20: educación/ubicación/modalidad).\n"
        "Evalúa explicitando la evidencia encontrada en el JSON del CV para cada bloque.\n"
        "Si hay discrepancias entre 'PERFIL DEL POSTULANTE' y 'CV_JSON' en identidad/ubicación, prioriza 'CV_JSON'.\n"
        "Responde SOLO JSON: {score:int 0..100, feedback:str 1–3 frases}."
    )


def _comparison_prompt_v3(applicant_profile: dict, vacancy_profile: dict, cv_json: dict) -> str:
    cv_json_norm = dict(cv_json or {})
    cv_json_norm["_habilidades_tokens"] = _canonicalize_terms(cv_json.get("habilidades", []))
    for exp in cv_json_norm.get("experiencia", []) or []:
        funcs = exp.get("funciones") or []
        exp["_funciones_tokens"] = _canonicalize_terms(funcs)

    return f"""
[PERFIL DEL POSTULANTE]
- Residencia: {applicant_profile.get('residence_addr')}
- Edad: {applicant_profile.get('age')}
- Años en el rol: {applicant_profile.get('role_exp_years')}
- Aspiración salarial: {applicant_profile.get('expected_salary')}
- Identificación: {applicant_profile.get('credential')}
- Teléfono: {applicant_profile.get('phone')}

[PERFIL DEL CARGO]
- Cargo: {vacancy_profile.get('charge_title')}
- Área: {vacancy_profile.get('charge_area')}
- Objetivo del rol: {vacancy_profile.get('role_objective')}
- Modalidad: {vacancy_profile.get('modality')}
- Ubicación: {vacancy_profile.get('location')}
- Responsabilidades: {vacancy_profile.get('responsibilities')}
- Requisitos (educación): {vacancy_profile.get('req_education')}
- Requisitos (experiencia): {vacancy_profile.get('req_experience')}
- Requisitos (conocimientos): {vacancy_profile.get('req_knowledge')}
- Descripción del cargo: {vacancy_profile.get('charge_description')}

[CV_JSON — SOLO EVIDENCIA DEL CV (+ vistas tokenizadas genéricas)]
{json.dumps(cv_json_norm, ensure_ascii=False)}

GUÍAS DE EVALUACIÓN (GENÉRICAS, MULTI-INDUSTRIA)
- Distingue entre competencias núcleo del rol, herramientas de soporte y habilidades blandas a partir de los textos de requisitos y responsabilidades de la vacante.
- No sobre-ponderes herramientas de soporte frente a competencias núcleo del rol.
- Si 'funciones' está vacío pero existen 'puesto' y 'periodo', puntúa experiencia con base en esos campos (sin inventar funciones).
- Para roles de entrada (ej.: pasantía, intern, trainee, junior), considera los requerimientos secundarios como deseables: su ausencia debe impactar menos que la falta de competencias núcleo.
- Mantén coherencia con la modalidad/ubicación/educación solicitadas para el ajuste general.

INSTRUCCIONES
1) Puntúa experiencia (0..40) usando 'experiencia' del CV_JSON (puesto, periodo y, si existen, funciones).
2) Puntúa conocimientos (0..40) comparando los requerimientos de la vacante con la evidencia ('habilidades' y, si aplica, funciones o logros) del CV_JSON.
3) Puntúa ajuste general (0..20) con educación, idioma.
4) No inventes datos fuera del CV_JSON. Si algo no está, no lo cuentes como evidencia.
5) No califiques la ubicacion de la residencia del postulante.
6) Da automaticamente una calificación de 0 por incompatibilidad del perfil con la vacante, y explica claramente la razón en el feedback.
7) Devuelve SOLO JSON:
{{
  "score": <entero 0..100>,
  "feedback": "<frases concisas>"
}}
"""


def score_candidate_v3(applicant_profile: dict, vacancy_profile: dict, cv_json: dict) -> dict:
    """
    v3 (Pin-Pon): usa el JSON del CV (evidencia) para evaluar contra el perfil de vacante + postulante.
    Reglas genéricas, sin hardcode de dominios o stacks.
    """
    messages = [
        {"role": "system", "content": _system_prompt_v3()},
        {"role": "user", "content": _comparison_prompt_v3(applicant_profile, vacancy_profile, cv_json)},
    ]
    raw = _post_chat(messages, response_format="json_object", temperature=0, max_tokens=min(900, AI_MAX_TOKENS))
    try:
        obj = json.loads(raw)
    except Exception:
        obj = {"score": 0, "feedback": "Formato inválido (no-JSON)."}
    return {
        "score": _clamp(obj.get("score"), 0, 100),
        "feedback": (obj.get("feedback") or "").strip() or "Sin comentarios.",
    }


# =======================================================
# Helpers públicos para orquestación externa
# =======================================================
__all__ = [
    "_post_chat",
    "_clamp",
    "score_candidate",        
    "score_candidate_v2",     
    "summarize_cv_to_json",  
    "score_candidate_v3",     
]
