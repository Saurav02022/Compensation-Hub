"""use byte-order collation for employee text columns

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = (
    ("employee_code", 20),
    ("full_name", 200),
    ("country", 100),
    ("department", 100),
    ("job_title", 100),
)


def upgrade() -> None:
    for name, length in COLUMNS:
        op.alter_column(
            "employees",
            name,
            type_=sa.String(length, collation="C"),
            existing_type=sa.String(length),
            existing_nullable=False,
        )


def downgrade() -> None:
    for name, length in COLUMNS:
        op.alter_column(
            "employees",
            name,
            type_=sa.String(length),
            existing_type=sa.String(length, collation="C"),
            existing_nullable=False,
        )
