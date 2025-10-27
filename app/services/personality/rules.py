# app/services/personality/rules.py

# Estilos DISC como "rasgos" agregados
TRAITS = ["dominant", "influential", "steady", "conscientious"]

# Para cada pregunta Q01..Q26:
#   1 (A) → dominant
#   2 (B) → influential
#   3 (C) → steady
#   4 (D) → conscientious
#
# Sumamos +1 al estilo elegido.
# (Si migras al formato de ranking 1..4 por pregunta, cambia +1 por +<puntaje_asignado>)

SCORING_RULES = {}

for i in range(1, 27):  # Q01..Q26
    qcode = f"Q{i:02d}"
    SCORING_RULES[qcode] = {
        1: {"dominant": 1},        # A
        2: {"influential": 1},     # B
        3: {"steady": 1},          # C
        4: {"conscientious": 1},   # D
    }

def overall_and_reco(traits_scores: dict) -> tuple[int, str]:
    """
    - overall_score: porcentaje del estilo principal (0..100)
    - recommendation: "PRIMARIO / SECUNDARIO" (p.ej. "Dominant / Influential")
    """
    # Evitar división por cero
    total_items = sum(traits_scores.values()) if traits_scores else 0
    if total_items <= 0:
        return 0, "Sin datos"

    # Ordenar estilos por puntaje
    ordered = sorted(traits_scores.items(), key=lambda kv: kv[1], reverse=True)
    primary_key, primary_score = ordered[0]
    secondary_key, _ = ordered[1] if len(ordered) > 1 else (None, 0)

    # % del principal como "overall"
    overall_pct = round((primary_score / max(total_items, 1)) * 100)

    # Etiquetas bonitas
    labels = {
        "dominant": "Dominant",
        "influential": "Influential",
        "steady": "Steady",
        "conscientious": "Conscientious",
    }
    primary_label = labels.get(primary_key, primary_key)
    secondary_label = labels.get(secondary_key, secondary_key) if secondary_key else "N/A"

    recommendation = f"{primary_label} / {secondary_label}"
    return overall_pct, recommendation
