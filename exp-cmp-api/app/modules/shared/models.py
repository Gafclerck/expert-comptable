import uuid

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPkMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)