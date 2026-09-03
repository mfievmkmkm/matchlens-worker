from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str,Enum):
    url="url"
    telegram="telegram"

class AnalysisMode(str,Enum):
    player="player"
    team="team"
    full="full"

class MatchSource(BaseModel):
    type: SourceType
    ref: str

class MatchTarget(BaseModel):
    player: str = Field(min_length=2,max_length=200)
    tracker_id: int|None = None
    team_id: int|None = None

class MatchCreate(BaseModel):
    source: MatchSource
    target: MatchTarget
    mode: AnalysisMode = AnalysisMode.full
    outputs: list[str] = Field(default_factory=lambda:["radar","player_stats","coach_report"])

class MatchJob(BaseModel):
    id: str
    status: str
    progress: int = 0
    stage: str = "queued"
    created_at: str = Field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
    request: MatchCreate
    result_url: str|None = None
    report_url: str|None = None
    error: str|None = None

class TargetSelection(BaseModel):
    tracker_id: int = Field(ge=1)
