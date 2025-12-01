"""SQLAlchemy database models."""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Formula(Base):
    """Selection formula model."""

    __tablename__ = "formulas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationship to screening results
    results: Mapped[list["ScreeningResult"]] = relationship(
        back_populates="formula",
        cascade="all, delete-orphan"
    )


class ScreeningResult(Base):
    """Screening result snapshot model."""

    __tablename__ = "screening_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    formula_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("formulas.id"),
        nullable=False
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    result_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Relationship to formula
    formula: Mapped["Formula"] = relationship(back_populates="results")


class BondCache(Base):
    """Bond data cache model."""

    __tablename__ = "bond_cache"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
