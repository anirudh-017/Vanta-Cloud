from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from .database import Base


# ============================================================
# USER ROLES
# ============================================================

class UserRole(str, Enum):

    ADMIN = "admin"

    MEMBER = "member"


# ============================================================
# USER MODEL
# ============================================================

class User(Base):

    __tablename__ = "users"


    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )


    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )


    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )


    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.MEMBER.value,
    )


    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda:
            datetime.now(timezone.utc),
    )
# ============================================================
# USER PREFERENCE MODEL
# ============================================================

class UserPreference(Base):

    __tablename__ = "user_preferences"


    user_id: Mapped[int] = mapped_column(

        ForeignKey(
            "users.id"
        ),

        primary_key=True,

    )


    theme: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )


    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda:
            datetime.now(timezone.utc),
        onupdate=lambda:
            datetime.now(timezone.utc),
    )

# ============================================================
# FILE RECORD MODEL
# ============================================================

class FileRecord(Base):

    __tablename__ = "files"


    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )


    stored_path: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        index=True,
        nullable=False,
    )


    original_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )


    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )


    uploaded_by_id: Mapped[int | None] = mapped_column(

        ForeignKey(
            "users.id"
        ),

        nullable=True,

        index=True,

    )


    is_trashed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )


    trashed_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda:
            datetime.now(timezone.utc),
    )


# ============================================================
# APP SETTING MODEL
# ============================================================
#
# Settings are stored as key/value pairs.
#
# Example:
#
# theme                  -> dark
# allow_member_uploads   -> true
# trash_retention_days   -> 30
#
# This means adding future settings does NOT require
# adding new SQLite columns every time.
# ============================================================

class AppSetting(Base):

    __tablename__ = "settings"


    key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )


    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda:
            datetime.now(timezone.utc),
        onupdate=lambda:
            datetime.now(timezone.utc),
    )
    # ============================================================
# ACTIVITY LOG MODEL
# ============================================================

class ActivityLog(Base):

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id"
        ),
        nullable=True,
        index=True,
    )

    actor_username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    target_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda:
            datetime.now(timezone.utc),
        index=True,
    )