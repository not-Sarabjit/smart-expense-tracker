from sqlalchemy import Column, Integer, String, Enum, Date, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database.base import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category_type = Column(Enum("expense", "income", name="category_type"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id",ondelete='CASCADE'), nullable=True)  ## User ID to store custom categories made by users
    created_at = Column(Date, server_default=func.current_date())

    ## Unique values constraints so duplicate categories are not made
    __table_args__ = (
        UniqueConstraint("user_id", "name", "category_type", name="uq_user_category_name_type"),
    )

    # Relationship Definition

    # With User
    user = relationship(
        'User',
        back_populates='custom_categories'
    )

    # With transactions
    transactions = relationship(
        'Transaction',
        back_populates='category',
        cascade='all, delete-orphan'
    )