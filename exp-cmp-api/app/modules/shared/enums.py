from enum import Enum as PyEnum
from typing import Type

from sqlalchemy import Enum as SAEnum


def sa_enum(enum_cls: Type[PyEnum], length: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda cls: [member.value for member in cls],
    )