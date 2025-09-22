from __future__ import annotations

from pydantic import BaseModel


class EffectsAPIResult(BaseModel):
    output_path: str | None
    width: int
    height: int
    bytes_written: int
    extra: dict



