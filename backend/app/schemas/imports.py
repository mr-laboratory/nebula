"""Response for a file import: a draft the editor fills in, never saved by the server."""

from pydantic import BaseModel, Field


class ImportedPost(BaseModel):
    title: str
    content: str = Field(description="Markdown")
    removed_images: int = Field(description="Images in the file that were not imported")
