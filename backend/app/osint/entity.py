"""Canonical resolved entities. `Person` is the primary specialization (people memory summarises a saved person's linked profile);
`EntityType` + `Relationship` generalize it for the knowledge graph.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EntityType(str, Enum):
    PERSON = "person"
    COMPANY = "company"
    REPOSITORY = "repository"
    TECHNOLOGY = "technology"
    PRODUCT = "product"
    CONFERENCE = "conference"
    UNKNOWN = "unknown"


@dataclass
class Person:
    name: str = ""
    github: str = ""
    company: str = ""
    website: str = ""
    bio: str = ""
    location: str = ""
    aliases: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def type(self) -> EntityType:
        return EntityType.PERSON

    @property
    def id(self) -> str:
        key = (self.github or self.name).strip().lower()
        return f"person:{key}"

    def is_empty(self) -> bool:
        return not any([self.name, self.github, self.company, self.website, self.bio, self.location])

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["id"] = self.id
        d["type"] = self.type.value
        return d


@dataclass
class Relationship:
    """A directed edge for the knowledge graph: subject --predicate--> obj."""
    subject: str
    predicate: str
    obj: str
    confidence: float = 0.5
    provider: str | None = None

    def key(self) -> tuple[str, str, str]:
        return (self.subject.lower(), self.predicate.lower(), self.obj.lower())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
