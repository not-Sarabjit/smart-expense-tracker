from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.sql import func
from app.database.base import Base

# Table Definition for Users that will use the app
class User(Base):

    # Name of the sql table in database
    __tablename__ = 'users'

    # Column Definitions
    id= Column(Integer, primary_key=True, index=True)
    email = Column(String,unique=True, index=True, nullable=False)
    first_name = Column(String, nullable = False)
    last_name = Column(String)
    hashed_password = Column(String, nullable=False)
    created_at = Column(Date,server_default = func.current_date())

