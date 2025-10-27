# app/services/personality/attempt_service.py
from datetime import datetime, timedelta
from typing import Iterable
from app.ext.db import db
from app.repositories.personality_repo import PersonalityRepository
from app.models.web_portal.postulation import Postulation
from .static_engine import StaticScoringEngine

class PersonalityAttemptService:
    def __init__(self, repo: PersonalityRepository | None = None):
        self.repo = repo or PersonalityRepository()
        self.engine = StaticScoringEngine()

    def bootstrap(self, *, postulation: Postulation, default_time_limit_sec: int | None = None) -> dict:
        attempt = self.repo.get_attempt_by_postulation(postulation.id)
        now = datetime.utcnow()

        if not attempt:
            attempt = self.repo.create_attempt(postulation=postulation, time_limit_sec=default_time_limit_sec)
            self.repo.mark_started(
                attempt,
                now=now,
                expires_at=(now + timedelta(seconds=attempt.time_limit_sec)) if attempt.time_limit_sec else None
            )
            db.session.commit()

        if attempt.expires_at and now >= attempt.expires_at and attempt.status in ("created", "started"):
            self.repo.mark_finished(attempt, now=now, expired=True)
            db.session.commit()

        return {
            "attempt_id": attempt.id,
            "status": attempt.status,
            "time_limit_sec": attempt.time_limit_sec,
            "expires_at": attempt.expires_at.isoformat() if attempt.expires_at else None,
            "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
        }

    def save_answers(self, *, attempt_id: int, answers: Iterable[dict]) -> None:
        now = datetime.utcnow()
        for a in answers:
            self.repo.upsert_answer(attempt_id, a["question_code"], int(a["option_value"]), now)
        db.session.commit()

    def finish(self, *, attempt_id: int) -> dict:
        from app.models.personality.attempt import PersonalityAttempt
        attempt = PersonalityAttempt.query.get_or_404(attempt_id)

        now = datetime.utcnow()
        expired = attempt.expires_at and now >= attempt.expires_at
        answers = [
            {"question_code": a.question_code, "option_value": a.option_value}
            for a in self.repo.list_answers(attempt.id)
        ]

        if not expired:
            scored = self.engine.score(answers)
            self.repo.save_results(
                attempt,
                traits=scored["traits"],
                overall=scored["overall_score"],
                reco=scored["recommendation"],
                pdf_path=None,
            )

        self.repo.mark_finished(attempt, now=now, expired=bool(expired))
        db.session.commit()

        return {
            "overall_score": attempt.overall_score or 0,
            "recommendation": attempt.recommendation or ("EXPIRADO" if expired else "N/A"),
            "traits": attempt.traits_json or {},
        }
