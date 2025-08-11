from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class StegoPayloadType(int, Enum):
    text = 1
    file = 2


class StegoLimits(BaseModel):
    max_cover_pixels: Optional[int] = Field(default=None, description="Max total pixels allowed for cover image")
    max_secret_bytes: Optional[int] = Field(default=None, description="Absolute max bytes of secret content")
    max_secret_ratio: float = Field(default=0.5, description="Max ratio of secret bytes to capacity bytes")


class StegoOptions(BaseModel):
    bits_per_channel: int = Field(default=1, ge=1, le=2)
    password: Optional[str] = None
    output_filename: Optional[str] = None
    limits: StegoLimits = Field(default_factory=StegoLimits)


class StegoTextHideRequest(BaseModel):
    text: str
    options: StegoOptions = Field(default_factory=StegoOptions)


class StegoTextRevealRequest(BaseModel):
    password: Optional[str] = None


class StegoFileHideRequest(BaseModel):
    options: StegoOptions = Field(default_factory=StegoOptions)


class StegoCapacityResult(BaseModel):
    capacity_bits: int
    capacity_bytes: int
    max_text_chars_no_password: int
    max_text_chars_with_password: int


class StegoHideResult(BaseModel):
    output_path: Path
    used_capacity_bits: int
    payload_size_bytes: int
    overhead_bytes: int
    encrypted: bool = False
    encryption: Optional[str] = None
    kdf: Optional[str] = None


class StegoRevealTextResult(BaseModel):
    text: str


class StegoRevealFileResult(BaseModel):
    output_path: Path
    filename: str
    size_bytes: int


