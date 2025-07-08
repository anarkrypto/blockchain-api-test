from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Address(Base):
    __tablename__ = 'addresses'

    address: Mapped[str] = mapped_column(String, primary_key=True)
    index: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )


class Balance(Base):
    __tablename__ = 'balances'

    address: Mapped[str] = mapped_column(
        String,
        ForeignKey('addresses.address'),
        primary_key=True,
        nullable=False,
    )
    chain_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        nullable=False,
    )
    amount: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )


class Transaction(Base):
    __tablename__ = 'transactions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Hash is not unique since a single transaction can transfer multiple
    # assets to multiple addresses (even the same address multiple times)
    hash: Mapped[str] = mapped_column(String, nullable=False, index=True)

    from_address: Mapped[str | None] = mapped_column(
        String,
        ForeignKey('addresses.address'),
        nullable=True,
    )
    to_address: Mapped[str | None] = mapped_column(
        String,
        ForeignKey('addresses.address'),
        nullable=True,
    )
    amount: Mapped[str] = mapped_column(String, nullable=False)
    chain_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        nullable=False,
    )
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )
