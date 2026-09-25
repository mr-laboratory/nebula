"""Auth request/response schemas. Passwords are SecretStr so they never appear in logs or reprs."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, EmailStr, Field, SecretStr

from app.schemas.common import lowercase

# NIST SP 800-63B: favour length over composition rules; cap length so hashing stays cheap.
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128


def _password_length(value: SecretStr) -> SecretStr:
    length = len(value.get_secret_value())
    if not PASSWORD_MIN_LENGTH <= length <= PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must be {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} characters long"
        )
    return value


Email = Annotated[EmailStr, AfterValidator(str.lower)]
Username = Annotated[str, BeforeValidator(lowercase), Field(pattern=r"^[a-z0-9_]{3,30}$")]
NewPassword = Annotated[SecretStr, AfterValidator(_password_length)]


class RegisterRequest(BaseModel):
    email: Email
    username: Username = Field(description="3-30 characters: lowercase letters, digits, _")
    password: NewPassword
    display_name: Annotated[str, Field(min_length=1, max_length=60)]


class LoginRequest(BaseModel):
    email: Email
    password: Annotated[SecretStr, Field(max_length=PASSWORD_MAX_LENGTH)]


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105  (OAuth2 token type, not a secret)
    expires_in: int = Field(description="Access token lifetime in seconds")
