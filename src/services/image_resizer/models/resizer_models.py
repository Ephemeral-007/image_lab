from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ResizeStrategy(str, Enum):
    fit_within = "fit_within"
    fill_and_crop = "fill_and_crop"
    stretch = "stretch"


class OutputFormat(str, Enum):
    jpeg = "jpeg"
    jpg = "jpg"
    png = "png"
    webp = "webp"
    tiff = "tiff"


class DimensionOptions(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None
    strategy: ResizeStrategy = ResizeStrategy.fit_within
    allow_upscale: bool = False


class TargetSizeOptions(BaseModel):
    target_size_kb: int = Field(..., gt=0)
    format_priority: List[OutputFormat] = Field(
        default_factory=lambda: [OutputFormat.webp, OutputFormat.jpeg, OutputFormat.png]
    )
    quality_min: int = 40
    quality_max: int = 95
    tolerance_kb: int = 3
    max_iterations: int = 12
    ssim_threshold: Optional[float] = Field(default=0.96, description="Stop if SSIM would go below this")


class ResizerInput(BaseModel):
    file_path: Optional[Path] = None
    image_bytes: Optional[bytes] = None
    url: Optional[str] = None


class ResizerOptions(BaseModel):
    dimensions: Optional[DimensionOptions] = None
    target_size: Optional[TargetSizeOptions] = None
    output_format: Optional[OutputFormat] = None
    background_rgba: tuple[int, int, int, int] = (255, 255, 255, 255)
    keep_metadata: bool = True


class ResizerResult(BaseModel):
    output_path: Optional[Path]
    output_format: OutputFormat
    width: int
    height: int
    bytes_written: int
    psnr: Optional[float] = None
    ssim: Optional[float] = None
    extra: Dict[str, str] = Field(default_factory=dict)


