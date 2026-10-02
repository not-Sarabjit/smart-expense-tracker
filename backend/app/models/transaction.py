import enum
from datetime import date as date_

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"


class TransactionSource(str, enum.Enum):
    """Where a transaction came from — provenance for audits and undo."""

    manual = "manual"
    chat = "chat"
    import_ = "import"
    schedule = "schedule"


class Transaction(Base):
    # Table Name Definition
    __tablename__ = "transactions"

    # Table Column Definitions
    id = Column(Integer, primary_key=True, index=True)

    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(SqlEnum(TransactionType, name="transaction_type"), nullable=False)
    description = Column(String(255), nullable=True)
    date = Column(Date, nullable=False, default=date_.today)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Provenance: manual | chat | import | schedule (values_callable stores the values, so
    # TransactionSource.import_ is persisted as "import")
    source = Column(
        SqlEnum(
            TransactionSource,
            name="transaction_source",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=TransactionSource.manual,
        server_default=TransactionSource.manual.value,
    )
    # Set by bulk imports; the FK to import_batches is added in Phase 8
    import_batch_id = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_transactions_user_id_date", "user_id", "date"),
        Index("ix_transactions_user_id_category_id", "user_id", "category_id"),
    )

    # Table Relationship Definitions

    # Relationship with user
    user = relationship("User", back_populates="transactions")

    # With Categories
    category = relationship("Category", back_populates="transactions")
