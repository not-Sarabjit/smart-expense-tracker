# backend/app/models/user.py
from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.database.base import Base


# Table Definition for Users that will use the app
class User(Base):
    # Name of the sql table in database
    __tablename__ = "users"

    # Column Definitions
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Preferences — the assistant needs both to format money and resolve "this month"
    currency = Column(String(3), nullable=False, default="INR", server_default="INR")  # ISO 4217
    timezone = Column(
        String(64), nullable=False, default="Asia/Kolkata", server_default="Asia/Kolkata"
    )  # IANA name

    # Relationship Definitions

    # With Transactions
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")

    # With user created custom categories
    custom_categories = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )

    # With conversations
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )