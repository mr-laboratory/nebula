"""Writing-check request and response: prose issues with offsets into the submitted text."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

IssueCategory = Literal["spelling", "grammar", "style", "punctuation", "other"]


class WritingCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=20_000, description="Markdown")
    language: str = Field(
        default="auto",
        pattern=r"^(auto|[a-z]{2,3}(-[A-Z]{2})?)$",
        description="`auto` to detect, or a code such as `en-US`",
    )


class WritingIssue(BaseModel):
    offset: int = Field(ge=0, description="Start, in UTF-16 code units (as in JavaScript)")
    length: int = Field(ge=0)
    message: str
    category: IssueCategory
    suggestions: list[str]


class WritingLanguage(BaseModel):
    code: str
    name: str


class WritingCheck(BaseModel):
    language: WritingLanguage
    issues: list[WritingIssue]
