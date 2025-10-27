# app/resources/__init__.py
from flask_smorest import Api
from flask import Flask

# Recursos públicos
from .health import blp as health_blp
from .web_portal.applicant import blp as applicants_blp
from .web_portal.vacancies import blp as PublicVacanciesBlp
from .web_portal.postulation import blp as PublicPostulationsBlp
from .web_portal.postulation_process import blp as PostulationProcessBlp 
from .web_portal.personality import blp as WebPortalPersonalityBlp 



# Recursos administrativos
from .admin.auth import blp as AdminAuthBlp
from .admin.users import blp as AdminUsersBlp
from .admin.charges import blp as AdminChargesBlp
from .admin.courses import blp as AdminCoursesBlp
from .admin.skill import blp as AdminSkillsBlp
from .admin.vacancies import blp as AdminVacanciesBlp
from .admin.vacancy_stats_resource import blp as AdminVacancyStatsBlp
from .admin.postulations_by_vacancy import blp as AdminPostulationsVacancyBlp
from .admin.postulations import blp_admin as AdminPostulationsBlp

# Recursos varios
from .upload_resource import blp as UploadsBlp
from .ai_scoring import blp as AIScoringBlp
from .terms import blp as TermsBlp 
from .guards import init_terms_guard

# Steps (Admin)
from .admin.steps.step1_accept import blp_admin_step1
from .admin.steps.step2_prescreen import blp as blp_admin_step2
from .admin.steps.step3_personality import blp as blp_admin_step3  
from .admin.steps.step4_schedule import blp as blp_admin_step4
from .admin.steps.step5_selection_pending import blp as blp_admin_step5
from .admin.steps.cancel import blp as blp_cancel_step


def register_resources(app: Flask) -> None:
    api = Api(app, spec_kwargs={
        "components": {"securitySchemes": {
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        }},
        "security": [{"BearerAuth": []}],
    })

    # Upload - S3 / AI scoring
    api.register_blueprint(UploadsBlp, url_prefix="/api/upload")
    api.register_blueprint(AIScoringBlp, url_prefix="/api")
    api.register_blueprint(TermsBlp, url_prefix="/api/terms")


    # Públicos
    api.register_blueprint(health_blp)
    api.register_blueprint(applicants_blp, url_prefix="/api/applicants")
    api.register_blueprint(PublicVacanciesBlp, url_prefix="/api/vacancies")
    api.register_blueprint(PublicPostulationsBlp, url_prefix="/api")
    api.register_blueprint(PostulationProcessBlp, url_prefix="/api") 
    api.register_blueprint(WebPortalPersonalityBlp, url_prefix="/api")  

    # Admin
    api.register_blueprint(AdminAuthBlp, url_prefix="/api/admin/auth")
    api.register_blueprint(AdminUsersBlp, url_prefix="/api/admin/users")
    api.register_blueprint(AdminChargesBlp, url_prefix="/api/admin/charges")
    api.register_blueprint(AdminCoursesBlp, url_prefix="/api/admin/courses")
    api.register_blueprint(AdminSkillsBlp, url_prefix="/api/admin/skills")
    api.register_blueprint(AdminVacanciesBlp, url_prefix="/api/admin/vacancies")
    api.register_blueprint(AdminVacancyStatsBlp, url_prefix="/api/admin/vacancies")
    api.register_blueprint(AdminPostulationsVacancyBlp, url_prefix="/api/admin/vacancies")
    api.register_blueprint(AdminPostulationsBlp, url_prefix="/api/admin/postulations")

    # Steps (Admin)
    api.register_blueprint(blp_admin_step1, url_prefix="/api/admin/postulations")
    api.register_blueprint(blp_admin_step2, url_prefix="/api/admin/postulations")
    api.register_blueprint(blp_admin_step3, url_prefix="/api/admin/postulations")  
    api.register_blueprint(blp_admin_step4, url_prefix="/api/admin/postulations")
    api.register_blueprint(blp_cancel_step, url_prefix="/api/admin/postulations")
    api.register_blueprint(blp_admin_step5, url_prefix="/api/admin/postulations")

    init_terms_guard(app)
