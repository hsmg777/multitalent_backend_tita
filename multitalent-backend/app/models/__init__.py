# app/models/__init__.py

from .postulation_ai_result import PostulationAIResult
from .terms_acceptance import TermsAcceptance

# Web portal
from .web_portal.applicant import Applicant
from .web_portal.postulation import Postulation

# Admin
from .admin.admin_user import AdminUser
from .admin.charges import Charges
from .admin.course import Course
from .admin.skill import Skill
from .admin.skills_courses import skills_courses  
from .admin.vacancy import Vacancy
from .admin.vacancy_skills import VacancySkill
from app.models.admin.interview import Interview
from app.models.admin.skill_grade import SkillGrade

# Personality Test
from .personality.attempt import PersonalityAttempt  
from .personality.answer import  PersonalityAnswer   