from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class ConversionAPIResult(BaseModel):
    output_path: Optional[str]
    output_format: str
    width: int
    height: int
    num_frames: int
    was_animated: bool
    metadata_preserved: bool
    bytes_written: Optional[int] = None


