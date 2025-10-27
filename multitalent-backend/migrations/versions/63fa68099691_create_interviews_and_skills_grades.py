"""create interviews and skills_grades

Revision ID: 63fa68099691
Revises: 95f231899033
Create Date: 2025-09-29 21:21:12.983437
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "63fa68099691"
down_revision = "95f231899033"
branch_labels = None
# Asegura que existan primero las tablas base
depends_on = ("80923210bb2e", "5d401438f7c4")  # create_postulations_table, create_skills_table


def upgrade():
    # ----------------------------
    # Tabla: interviews (1:1 con postulation)
    # ----------------------------
    op.create_table(
        "interviews",
        sa.Column("id", sa.Integer(), primary_key=True),

        # 1:1 con postulation (singular) + ON DELETE CASCADE
        sa.Column(
            "postulation_id",
            sa.Integer(),
            sa.ForeignKey("postulation.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),

        # Datos de la reunión
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("modality", sa.String(length=20), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("meet_url", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_interviews_postulation_id", "interviews", ["postulation_id"], unique=True)

    # ----------------------------
    # Tabla: skills_grades (pivot entrevista <-> skill)
    # ----------------------------
    op.create_table(
        "skills_grades",
        sa.Column("id", sa.Integer(), primary_key=True),

        sa.Column("interview_id", sa.Integer(), sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False),

        sa.Column("score", sa.Integer(), nullable=False),

        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),

        sa.UniqueConstraint("interview_id", "skill_id", name="uq_skills_grades_interview_skill"),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_skills_grades_score_0_100"),
    )
    op.create_index("ix_skills_grades_interview_id", "skills_grades", ["interview_id"], unique=False)
    op.create_index("ix_skills_grades_skill_id", "skills_grades", ["skill_id"], unique=False)


def downgrade():
    # Primero pivot, luego interviews (respeta dependencias)
    op.drop_index("ix_skills_grades_skill_id", table_name="skills_grades")
    op.drop_index("ix_skills_grades_interview_id", table_name="skills_grades")
    op.drop_table("skills_grades")

    op.drop_index("ix_interviews_postulation_id", table_name="interviews")
    op.drop_table("interviews")
