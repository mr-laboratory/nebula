"""User schemas. Fields are listed explicitly, so private columns like password_hash can't leak."""

import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserMe(BaseModel):
    """The signed-in user's own profile, including private fields (email) and access rights."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    display_name: str
    bio: str | None
    created_at: datetime
    roles: list[str]
    permissions: list[str]


class UserUpdate(BaseModel):
    display_name: Annotated[str, Field(min_length=1, max_length=60)] | None = None
    bio: Annotated[str, Field(max_length=280)] | None = None

    @model_validator(mode="after")
    def _not_empty(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        if "display_name" in self.model_fields_set and self.display_name is None:
            raise ValueError("display_name cannot be null")
        return self
