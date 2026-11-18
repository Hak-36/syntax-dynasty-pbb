from typing import Literal, Optional
from pydantic import BaseModel, Field

EntityType = Literal["company", "person"]
MeetingType = Literal["sales", "investor", "partnership", "interview", "general"]


class GenerateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    entity_type: EntityType
    meeting_time: str  # ISO string, e.g. 2026-11-20T15:00:00Z
    meeting_type: MeetingType = "general"


class Entity(BaseModel):
    name: str
    type: EntityType
    description: str
    disambiguation_note: Optional[str] = None


class Meeting(BaseModel):
    time: str
    type: MeetingType
    window_start: str
    window_end: str


class KeyDevelopment(BaseModel):
    date: Optional[str] = None
    category: str
    text: str
    confidence: Literal["verified", "uncertain"]
    source_ids: list[int] = []
    note: Optional[str] = None


class Point(BaseModel):
    text: str
    source_ids: list[int] = []


class Source(BaseModel):
    id: int
    title: str
    url: str
    published_date: Optional[str] = None
    domain: str


class Meta(BaseModel):
    generated_at: str
    models_used: list[str] = []
    provider_used: Optional[str] = None
    fallback_used: bool = False
    latency_seconds: float
    notes: Optional[str] = None


class GenerateResponse(BaseModel):
    entity: Entity
    meeting: Meeting
    snapshot: str
    snapshot_source_ids: list[int] = []
    key_developments: list[KeyDevelopment] = []
    talking_points: list[Point] = []
    risks: list[Point] = []
    questions: list[str] = []
    sources: list[Source] = []
    meta: Meta