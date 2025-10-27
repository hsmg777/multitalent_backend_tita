# app/repositories/personality_repo.py
from datetime import datetime
from typing import Iterable
from app.ext.db import db
from app.models.personality.attempt import PersonalityAttempt
from app.models.personality.answer import PersonalityAnswer
from app.models.web_portal.postulation import Postulation

class PersonalityRepository:
    def get_attempt_by_postulation(self, postulation_id: int) -> PersonalityAttempt | None:
        return PersonalityAttempt.query.filter_by(postulation_id=postulation_id).one_or_none()

    def create_attempt(self, *, postulation: Postulation, time_limit_sec: int | None) -> PersonalityAttempt:
        attempt = PersonalityAttempt(
            postulation_id=postulation.id,
            applicant_id=postulation.applicant_id,
            vacancy_id=postulation.vacancy_id,
            status="created",
            time_limit_sec=time_limit_sec,
        )
        db.session.add(attempt)
        return attempt

    def mark_started(self, attempt: PersonalityAttempt, now: datetime, expires_at: datetime | None) -> None:
        attempt.status = "started"
        attempt.started_at = now
        attempt.expires_at = expires_at

    def upsert_answer(self, attempt_id: int, question_code: str, option_value: int, at: datetime) -> PersonalityAnswer:
        ans = PersonalityAnswer.query.filter_by(attempt_id=attempt_id, question_code=question_code).one_or_none()
        if ans:
            ans.option_value = option_value
            ans.answered_at = at
            return ans
        ans = PersonalityAnswer(attempt_id=attempt_id, question_code=question_code, option_value=option_value, answered_at=at)
        db.session.add(ans)
        return ans

    def list_answers(self, attempt_id: int) -> list[PersonalityAnswer]:
        return PersonalityAnswer.query.filter_by(attempt_id=attempt_id).all()

    def mark_finished(self, attempt: PersonalityAttempt, *, now: datetime, expired: bool) -> None:
        attempt.finished_at = now
        attempt.status = "expired" if expired else "finished"
        if attempt.started_at:
            attempt.duration_sec = int((now - attempt.started_at).total_seconds())

    def save_results(self, attempt: PersonalityAttempt, *, traits: dict, overall: int, reco: str, pdf_path: str | None = None) -> None:
        attempt.traits_json = traits
        attempt.overall_score = overall
        attempt.recommendation = reco
        attempt.pdf_report_path = pdf_path
