# app/services/personality/engine_interface.py
from typing import Protocol

class PersonalityScoringEngine(Protocol):
    def score(self, answers: list[dict]) -> dict:
        """returns: { traits: {...}, overall_score: int, recommendation: str, notes: list[str] }"""
        ...
