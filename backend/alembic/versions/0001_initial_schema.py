"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("employee_code", sa.String(length=20), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("job_title", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employees")),
        sa.UniqueConstraint("employee_code", name=op.f("uq_employees_employee_code")),
    )
    op.create_table(
        "fx_rates",
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("rate_to_usd", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.CheckConstraint(
            "currency_code ~ '^[A-Z]{3}$'", name=op.f("ck_fx_rates_currency_code_format")
        ),
        sa.CheckConstraint("rate_to_usd > 0", name=op.f("ck_fx_rates_rate_to_usd_positive")),
        sa.PrimaryKeyConstraint("currency_code", name=op.f("pk_fx_rates")),
    )
    op.create_table(
        "compensation",
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("annual_salary", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.CheckConstraint(
            "annual_salary > 0", name=op.f("ck_compensation_annual_salary_positive")
        ),
        sa.ForeignKeyConstraint(
            ["currency_code"],
            ["fx_rates.currency_code"],
            name=op.f("fk_compensation_currency_code_fx_rates"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name=op.f("fk_compensation_employee_id_employees"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("employee_id", name=op.f("pk_compensation")),
    )


def downgrade() -> None:
    op.drop_table("compensation")
    op.drop_table("fx_rates")
    op.drop_table("employees")
