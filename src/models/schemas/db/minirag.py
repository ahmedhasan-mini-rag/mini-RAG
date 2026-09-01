import uuid
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import UUID, String, DateTime, func, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    ...


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(), 
        primary_key=True, 
        default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(25), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    assets: Mapped[list["Asset"]] = relationship(back_populates="project")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="project")

class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(), 
        primary_key=True, 
        default=uuid.uuid4
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    asset_type: Mapped[str] = mapped_column()
    asset_name: Mapped[str] = mapped_column()
    asset_size: Mapped[int] = mapped_column()
    asset_config: Mapped[dict | None] = mapped_column(JSONB)

    asset_project_id: Mapped[uuid.UUID] = mapped_column(UUID(), ForeignKey("projects.id"))

    project: Mapped["Project"] = relationship(back_populates="assets")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="asset")

    __table_args__ = (
        Index("ix_asset_project_id_asset_name", "asset_project_id", "asset_name", unique=True),
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4
    )

    chunk_metadata: Mapped[dict] = mapped_column(JSONB)

    chunk_project_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("projects.id"), index=True)
    chunk_asset_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("assets.id"), index=True)

    project: Mapped["Project"] = relationship(back_populates="chunks")
    asset: Mapped["Asset"] = relationship(back_populates="chunks")
    