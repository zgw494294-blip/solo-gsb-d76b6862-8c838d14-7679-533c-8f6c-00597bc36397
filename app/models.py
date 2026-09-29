from collections import defaultdict
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Subtitle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    speaker: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    locked_track: Optional[int] = Field(default=None, ge=1)

    @field_validator("start_ms", "end_ms", "locked_track", mode="before")
    @classmethod
    def reject_boolean_numbers(cls, value):
        if isinstance(value, bool):
            raise ValueError("must be an integer, not a boolean")
        return value

    @model_validator(mode="after")
    def validate_interval(self):
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self


class AssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track_count: int = Field(ge=2, le=3)
    subtitles: list[Subtitle] = Field(min_length=1, max_length=12)

    @field_validator("track_count", mode="before")
    @classmethod
    def reject_boolean_track_count(cls, value):
        if isinstance(value, bool):
            raise ValueError("must be an integer, not a boolean")
        return value

    @model_validator(mode="after")
    def validate_request_constraints(self):
        seen_ids: set[str] = set()
        intervals_by_speaker: dict[str, list[tuple[int, int]]] = defaultdict(list)

        for subtitle in self.subtitles:
            if subtitle.id in seen_ids:
                raise ValueError(f"duplicate subtitle id: {subtitle.id}")
            seen_ids.add(subtitle.id)

            if (
                subtitle.locked_track is not None
                and subtitle.locked_track > self.track_count
            ):
                raise ValueError(
                    f"locked_track {subtitle.locked_track} is out of range "
                    f"for {self.track_count} tracks"
                )

            intervals_by_speaker[subtitle.speaker].append(
                (subtitle.start_ms, subtitle.end_ms)
            )

        for speaker, intervals in intervals_by_speaker.items():
            intervals.sort()
            previous_end: Optional[int] = None
            for start, end in intervals:
                if previous_end is not None and start < previous_end:
                    raise ValueError(
                        f"subtitles for speaker {speaker!r} must not overlap"
                    )
                if previous_end is None or end > previous_end:
                    previous_end = end

        return self


class TrackAssignment(BaseModel):
    id: str
    track: int


class AssignmentResponse(BaseModel):
    solvable: bool
    assignments: list[TrackAssignment] = Field(default_factory=list)
    track_changes: int = 0
