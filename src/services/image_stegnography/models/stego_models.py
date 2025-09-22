from __future__ import annotations

import enum
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set, Union

from pydantic import BaseModel, Field


class StegoPayloadType(int, Enum):
    text = 1
    file = 2
    compressed = 3  # New type for compressed payloads


class StegoLimits(BaseModel):
    max_cover_pixels: Optional[int] = Field(default=None, description="Max total pixels allowed for cover image")
    max_secret_bytes: Optional[int] = Field(default=None, description="Absolute max bytes of secret content")
    max_secret_ratio: float = Field(default=0.5, description="Max ratio of secret bytes to capacity bytes")


class RGBChannel(str, Enum):
    RED = "R"
    GREEN = "G"
    BLUE = "B"
    ALL = "RGB"


class ErrorCorrectionLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StegoOptions(BaseModel):
    bits_per_channel: int = Field(default=1, ge=1, le=8, description="Number of least significant bits to use (1-8)")
    password: Optional[str] = None
    output_filename: Optional[str] = None
    limits: StegoLimits = Field(default_factory=StegoLimits)
    channels: Union[RGBChannel, List[RGBChannel]] = Field(default=RGBChannel.ALL, description="RGB channels to use")
    error_correction: ErrorCorrectionLevel = Field(default=ErrorCorrectionLevel.NONE, description="Error correction level")
    compress: bool = Field(default=False, description="Whether to compress payload before embedding")


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
    capacity_per_channel: dict[str, int] = Field(default_factory=dict, description="Capacity in bits per channel")


class StegoHideResult(BaseModel):
    output_path: Path
    used_capacity_bits: int
    payload_size_bytes: int
    overhead_bytes: int
    encrypted: bool = False
    encryption: Optional[str] = None
    kdf: Optional[str] = None
    compression: Optional[str] = None
    compression_ratio: Optional[float] = None
    channels_used: List[str] = Field(default_factory=list)
    bits_per_channel: int = 1


class StegoRevealTextResult(BaseModel):
    text: str
    was_compressed: bool = False
    channels_used: List[str] = Field(default_factory=list)
    bits_per_channel: int = 1


class StegoRevealFileResult(BaseModel):
    output_path: Path
    filename: str
    size_bytes: int
    was_compressed: bool = False
    channels_used: List[str] = Field(default_factory=list)
    bits_per_channel: int = 1


class BitPlaneVisualizerResult(BaseModel):
    output_images: List[Path]
    channel: str
    bit_plane: int