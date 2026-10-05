"""Base declarative class, shared column types and mixins.

All SCIX tables inherit ``UUIDPrimaryKeyMixin`` so that identifiers are UUIDs rather
than sequences: datasets are created on multiple machines by collaboration and export
workers, and a shared sequence is a contention and offline-merge hazard.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, MetaData, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Bare `dict` and `list` are JSONB. Subscripted generics (list[str]) cannot be
    # used in annotations -- declare the bare builtin and mark nullability with `| None`.
    type_annotation_map = {dict: JSONB, list: JSONB}


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def enum_col(enum_cls: type[enum.Enum], name: str, **kwargs) -> Column:
    """A native Postgres enum column.

    Native enums rather than VARCHAR+CHECK so that adding a value is a visible schema
    migration, and so the database rejects a value the application never intended to
    accept -- notably test names and graph types, which are the registries the spec fixes.

    Returns a Core ``Column`` so it can be called from a helper outside the declarative
    class body. Use it as the whole assignment, with the annotation carrying the type::

        role: Mapped[UserRole] = enum_col(UserRole, "user_role")
    """
    return Column(
        SAEnum(enum_cls, name=name, native_enum=True, validate_strings=True),
        nullable=False,
        **kwargs,
    )


def optional_enum_col(enum_cls: type[enum.Enum], name: str, **kwargs) -> Column:
    return Column(
        SAEnum(enum_cls, name=name, native_enum=True, validate_strings=True),
        nullable=True,
        **kwargs,
    )
