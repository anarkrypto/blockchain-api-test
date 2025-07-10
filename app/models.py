import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
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

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    address: Mapped[str] = mapped_column(
        String,
        ForeignKey('addresses.address'),
        nullable=False,
    )
    chain_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    balance: Mapped[str] = mapped_column(String, nullable=False, default='0')

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP'),
    )

    # Ensure one balance per address/chain/token combination
    __table_args__ = (
        UniqueConstraint(
            'address', 'chain_id', 'token', name='unique_balance'
        ),
    )


class Transaction(Base):
    __tablename__ = 'transactions'

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

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
    status: Mapped[str] = mapped_column(
        String, nullable=False, default='pending'
    )
    gas_used: Mapped[str | None] = mapped_column(String, nullable=True)
    gas_price: Mapped[str | None] = mapped_column(String, nullable=True)
    fee: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )


class ProcessedTransaction(Base):
    __tablename__ = 'processed_transactions'

    hash: Mapped[str] = mapped_column(String, primary_key=True)
    chain_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
    )
