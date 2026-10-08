from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class PatientRecord(Base):
    __tablename__ = "patient_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    assessment_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    patient_ref: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    education: Mapped[float | None] = mapped_column(Float, nullable=True)
    mmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    adas: Mapped[float | None] = mapped_column(Float, nullable=True)
    faq: Mapped[float | None] = mapped_column(Float, nullable=True)
    sex: Mapped[float | None] = mapped_column(Float, nullable=True)
    moca: Mapped[float | None] = mapped_column(Float, nullable=True)

    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    model_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )