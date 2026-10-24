from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class Item(StrictModel):
    id: str = Field(pattern=r"^LF-(?:\d{3}|[a-f0-9]{12})$")
    type: str = Field(min_length=1, max_length=80)
    colour: str = Field(min_length=1, max_length=60)
    features: list[str] = Field(min_length=1, max_length=6)
    description: str = Field(min_length=10, max_length=600)

    place: str = Field(default="Not recorded", max_length=160)
    created_at: int = 0

class Match(StrictModel):
    id: str
    evidence: list[str] = Field(min_length=1, max_length=4)

class ModelResult(StrictModel):
    status: Literal["matches", "no_match", "clarify"]
    matches: list[Match] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def consistent(self):
        if (self.status == "matches") != bool(self.matches):
            raise ValueError("Status and matches disagree")
        if len({m.id for m in self.matches}) != len(self.matches):
            raise ValueError("Duplicate IDs")
        return self

class SearchResult(BaseModel):
    status: Literal["matches", "no_match", "clarify", "refused", "invalid", "unavailable", "error"]
    mode: str
    message: str
    matches: list[Match] = Field(default_factory=list)
