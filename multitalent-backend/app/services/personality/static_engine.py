# app/services/personality/static_engine.py  (reemplaza todo el archivo)

class StaticScoringEngine:
    """
    Suma forzada por letra DISC:
      - question_code = "Qnn_A".."Qnn_D"
      - option_value  = 1..4
    Resultado: totales por A/B/C/D y porcentajes.
    """
    LETTERS = ("A", "B", "C", "D")

    def score(self, answers: list[dict]) -> dict:
        totals = {l: 0 for l in self.LETTERS}  
        counts = {l: 0 for l in self.LETTERS}  

        for a in answers:
            qcode_full = str(a["question_code"])
            val = int(a["option_value"])
            try:
                letter = qcode_full.split("_")[1].upper()  
            except Exception:
                continue
            if letter not in self.LETTERS:
                continue
            totals[letter] += val
            counts[letter] += 1

        # porcentajes simples sobre suma máxima posible
        # Máximo por letra = 26 preguntas * 4 puntos = 104
        max_per_letter = max(counts.values()) * 4 if max(counts.values()) > 0 else 0
        percents = {}
        if max_per_letter > 0:
            percents = {l: round((totals[l] / max_per_letter) * 100, 1) for l in self.LETTERS}
        else:
            percents = {l: 0.0 for l in self.LETTERS}

        winner = max(self.LETTERS, key=lambda l: totals[l])
        overall = int(round(percents[winner])) if percents else 0

        reco = "APTO"

        notes = [f"Estilo predominante: {winner}"]

        traits = {
            "totals": totals,       
            "percents": percents,    
        }

        return {
            "traits": traits,
            "overall_score": overall,
            "recommendation": reco,
            "notes": notes,
        }
