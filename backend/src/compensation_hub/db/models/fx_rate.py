from decimal import Decimal

from sqlalchemy import CheckConstraint, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from compensation_hub.db.base import Base


class FxRate(Base):
    """Seeded exchange rate used to normalize local salaries to USD for analytics."""

    __tablename__ = "fx_rates"
    __table_args__ = (
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency_code_format"),
        CheckConstraint("rate_to_usd > 0", name="rate_to_usd_positive"),
    )

    currency_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    rate_to_usd: Mapped[Decimal] = mapped_column(Numeric(18, 8))
