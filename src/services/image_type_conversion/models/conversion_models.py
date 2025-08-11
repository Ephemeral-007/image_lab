from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class TargetImageFormat(str, Enum):
    jpeg = "jpeg"
    jpg = "jpg"
    png = "png"
    webp = "webp"
    tiff = "tiff"
    bmp = "bmp"
    gif = "gif"
    pdf = "pdf"
    jp2 = "jp2"


class ConversionOptions(BaseModel):
    to_format: TargetImageFormat = Field(..., description="Target format to encode to")
    background_color: Optional[Tuple[int, int, int, int]] = Field(
        default=(255, 255, 255, 255), description="RGBA background for flattening transparency"
    )
    quality: Optional[int] = Field(
        default=90, description="Quality for lossy formats (e.g., JPEG, WEBP). Range 1-100"
    )
    optimize: bool = Field(default=True, description="Let encoder try to optimize output size")
    progressive: bool = Field(default=True, description="Save as progressive (where supported)")
    keep_metadata: bool = Field(default=True, description="Preserve EXIF/ICC where possible")
    keep_animation: bool = Field(
        default=False, description="If input is animated and target supports, keep animation"
    )
    dpi: Optional[Tuple[int, int]] = Field(default=None, description="DPI to embed when saving")
    lossless_webp: Optional[bool] = Field(
        default=None, description="Prefer lossless for WEBP (if True)"
    )
    png_compress_level: Optional[int] = Field(
        default=None, description="PNG compression level (0-9)"
    )


class ConversionInput(BaseModel):
    # Only one of the following should be provided
    file_path: Optional[Path] = None
    image_bytes: Optional[bytes] = None
    url: Optional[str] = None


class ConversionResult(BaseModel):
    output_path: Optional[Path]
    output_format: TargetImageFormat
    width: int
    height: int
    num_frames: int
    was_animated: bool
    metadata_preserved: bool
    bytes_written: Optional[int] = None
    extra: Dict[str, str] = Field(default_factory=dict)


class ResizeStrategy(str, Enum):
    fit_within = "fit_within"
    fill_and_crop = "fill_and_crop"
    stretch = "stretch"


class ResizeOptions(BaseModel):
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    strategy: ResizeStrategy = ResizeStrategy.fit_within
    allow_upscale: bool = False


class QuantizeOptions(BaseModel):
    num_colors: Optional[int] = Field(default=None, description="Palette size for PNG/GIF (e.g., 256)")
    dither: bool = True


class ColorProfileAction(str, Enum):
    none = "none"
    convert_to_srgb = "convert_to_srgb"
    assign_srgb = "assign_srgb"


class AdvancedConversionOptions(ConversionOptions):
    resize: Optional[ResizeOptions] = None
    quantize: Optional[QuantizeOptions] = None
    color_profile_action: ColorProfileAction = ColorProfileAction.convert_to_srgb
    compute_metrics: bool = False


class BatchConversionRequest(BaseModel):
    # One of the inputs
    file_path: Optional[Path] = None
    image_bytes: Optional[bytes] = None
    url: Optional[str] = None
    # Multiple targets
    targets: List[AdvancedConversionOptions]



