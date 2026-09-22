"""add employee directory indexes

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-22

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_employees_full_name_employee_code", "employees", ["full_name", "employee_code"]
    )
    op.create_index("ix_employees_country", "employees", ["country"])
    op.create_index("ix_employees_department", "employees", ["department"])
    op.create_index("ix_employees_job_title", "employees", ["job_title"])


def downgrade() -> None:
    op.drop_index("ix_employees_job_title", table_name="employees")
    op.drop_index("ix_employees_department", table_name="employees")
    op.drop_index("ix_employees_country", table_name="employees")
    op.drop_index("ix_employees_full_name_employee_code", table_name="employees")
