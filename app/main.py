"""FastAPI 入口：请求/响应模型与路由。"""
from __future__ import annotations

from typing import List, Optional, Union

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator, model_validator

from .solver import Subtitle, solve, validate

app = FastAPI(
    title="对白字幕分轨 API",
    description=(
        "为离线对白字幕分配屏幕轨道：时间重叠的字幕不同轨，"
        "同一说话人按时间相邻字幕的换轨次数最少，并列取轨道号序列字典序最小者。"
    ),
    version="1.0.0",
)


class SubtitleIn(BaseModel):
    id: Union[str, int] = Field(..., description="全局唯一的字幕 id")
    speaker: str = Field(..., description="说话人标识，非空")
    start_ms: int = Field(..., ge=0, description="开始时间（毫秒，非负）")
    end_ms: int = Field(..., ge=0, description="结束时间（毫秒，必须大于 start_ms）")
    locked_track: Optional[int] = Field(
        default=None, ge=1, description="可选：锁定轨道号（从 1 开始）"
    )

    @field_validator("speaker")
    @classmethod
    def _speaker_not_blank(cls, v: str) -> str:
        if v.strip() == "":
            raise ValueError("speaker 不能为空")
        return v

    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, v: Union[str, int]) -> Union[str, int]:
        if isinstance(v, str) and v == "":
            raise ValueError("id 不能为空字符串")
        return v

    @model_validator(mode="after")
    def _check_interval(self) -> "SubtitleIn":
        if self.start_ms >= self.end_ms:
            raise ValueError("start_ms 必须小于 end_ms")
        return self


class AssignRequest(BaseModel):
    track_count: int = Field(
        ..., ge=2, le=3, description="屏幕轨道数（2～3，轨道号从 1 开始）"
    )
    subtitles: List[SubtitleIn] = Field(
        ..., min_length=1, max_length=12, description="字幕列表（1～12 条，按输入顺序）"
    )

    @model_validator(mode="after")
    def _check_cross_item_rules(self) -> "AssignRequest":
        subs = [
            Subtitle(
                id=s.id,
                speaker=s.speaker,
                start_ms=s.start_ms,
                end_ms=s.end_ms,
                locked_track=s.locked_track,
            )
            for s in self.subtitles
        ]
        error = validate(subs, self.track_count)
        if error is not None:
            raise ValueError(error)
        return self


class TrackAssignment(BaseModel):
    id: Union[str, int]
    track: int


class AssignResponse(BaseModel):
    feasible: bool
    changes: int = Field(..., description="同一说话人按时间相邻字幕的换轨总数")
    assignments: List[TrackAssignment]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/assign", response_model=AssignResponse)
def assign(req: AssignRequest) -> AssignResponse:
    subs = [
        Subtitle(
            id=s.id,
            speaker=s.speaker,
            start_ms=s.start_ms,
            end_ms=s.end_ms,
            locked_track=s.locked_track,
        )
        for s in req.subtitles
    ]
    tracks, changes = solve(subs, req.track_count)
    if tracks is None:
        # 锁定冲突 / 轨道不足：无解，方案为空（HTTP 仍为 200；非法输入才是 422）
        return AssignResponse(feasible=False, changes=0, assignments=[])
    return AssignResponse(
        feasible=True,
        changes=changes,
        assignments=[
            TrackAssignment(id=s.id, track=t) for s, t in zip(subs, tracks)
        ],
    )
