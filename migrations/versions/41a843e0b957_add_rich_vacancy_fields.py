# migrations/versions/41a843e0b957_add_rich_vacancy_fields.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "41a843e0b957"
down_revision = "d27d8de9d269"
branch_labels = None
depends_on = None


def upgrade():
    # Añadimos columnas. Las JSONB NOT NULL llevan server_default para no romper con filas existentes.
    with op.batch_alter_table("vacancies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("role_objective", sa.Text(), nullable=True))

        batch_op.add_column(
            sa.Column(
                "responsibilities",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "req_education",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "req_experience",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "req_knowledge",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "benefits",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )

        batch_op.add_column(sa.Column("company_about", sa.Text(), nullable=True))

        batch_op.add_column(
            sa.Column(
                "tags",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )

        batch_op.add_column(sa.Column("hero_image_url", sa.String(length=500), nullable=True))

    # Asegura que las filas existentes queden con [] (por si el motor no aplicara el default a filas viejas)
    op.execute("UPDATE vacancies SET responsibilities='[]'::jsonb WHERE responsibilities IS NULL;")
    op.execute("UPDATE vacancies SET req_education='[]'::jsonb WHERE req_education IS NULL;")
    op.execute("UPDATE vacancies SET req_experience='[]'::jsonb WHERE req_experience IS NULL;")
    op.execute("UPDATE vacancies SET req_knowledge='[]'::jsonb WHERE req_knowledge IS NULL;")
    op.execute("UPDATE vacancies SET benefits='[]'::jsonb WHERE benefits IS NULL;")
    op.execute("UPDATE vacancies SET tags='[]'::jsonb WHERE tags IS NULL;")

    # (Opcional) Quitar server_default para que a futuro no se auto-completen si insertas NULL explícito.
    with op.batch_alter_table("vacancies", schema=None) as batch_op:
        batch_op.alter_column("responsibilities", server_default=None)
        batch_op.alter_column("req_education", server_default=None)
        batch_op.alter_column("req_experience", server_default=None)
        batch_op.alter_column("req_knowledge", server_default=None)
        batch_op.alter_column("benefits", server_default=None)
        batch_op.alter_column("tags", server_default=None)


def downgrade():
    with op.batch_alter_table("vacancies", schema=None) as batch_op:
        batch_op.drop_column("hero_image_url")
        batch_op.drop_column("tags")
        batch_op.drop_column("company_about")
        batch_op.drop_column("benefits")
        batch_op.drop_column("req_knowledge")
        batch_op.drop_column("req_experience")
        batch_op.drop_column("req_education")
        batch_op.drop_column("responsibilities")
        batch_op.drop_column("role_objective")
