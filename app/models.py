from sqlalchemy import Column, DateTime, Integer, String, text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Address(Base):
    __tablename__ = 'addresses'

    address = Column(String, primary_key=True)
    index = Column(Integer, unique=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )
