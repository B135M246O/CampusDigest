from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Author(BaseModel):
    """Схема - Автор статьи."""
    author_name: str

    class Config:
        orm_mode = True


class Infographic(BaseModel):
    """Схема - инфографика к статье."""
    infographic_link: str

    class Config:
        orm_mode = True


class Article(BaseModel):
    """Схема - Статья."""
    id: int
    source: str
    date: datetime
    category: str
    title: str
    overview: Optional[str]
    text: Optional[str]
    link: str
    picture_link: Optional[str]
    video_link: Optional[str]
    video_preview_link: Optional[str]
    authors: list[Author] = Field(default_factory=list)
    infographic_links: list[Infographic] = Field(default_factory=list)

    class Config:
        orm_mode = True
