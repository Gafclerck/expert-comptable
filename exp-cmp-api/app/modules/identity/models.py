import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, Table, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base
from app.modules.shared.enums import sa_enum
from app.modules.shared.models import UUIDPkMixin


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PersonStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class BusinessStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class BusinessAccountRole(str, Enum):
    OWNER = "owner"
    CUSTOMER = "customer"


class RoleCode(str, Enum):
    ROOT = "root"


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Person(UUIDPkMixin, Base):
    __tablename__ = "persons"

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[PersonStatus] = mapped_column(
        sa_enum(PersonStatus, length=20), nullable=False, default=PersonStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Role(UUIDPkMixin, Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class User(UUIDPkMixin, Base):
    __tablename__ = "users"

    person_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        sa_enum(UserStatus, length=20), nullable=False, default=UserStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    person: Mapped[Person | None] = relationship(lazy="selectin")
    roles: Mapped[list[Role]] = relationship(secondary=user_roles, lazy="selectin")


class Business(UUIDPkMixin, Base):
    __tablename__ = "businesses"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[BusinessStatus] = mapped_column(
        sa_enum(BusinessStatus, length=20), nullable=False, default=BusinessStatus.ACTIVE
    )


class BusinessAccount(UUIDPkMixin, Base):
    __tablename__ = "business_accounts"

    business_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("businesses.id"), nullable=False, index=True)
    person_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("persons.id"), nullable=False, index=True)
    role: Mapped[BusinessAccountRole] = mapped_column(
        sa_enum(BusinessAccountRole, length=20), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
