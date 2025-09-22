from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


class BackgroundActionType(str, Enum):
    remove = "remove"
    transparent = "transparent"
    blur = "blur"
    replace_color = "replace_color"
    replace_image = "replace_image"


class BackgroundAction(BaseModel):
    action: BackgroundActionType
    blur_radius: Optional[float] = Field(default=12.0, description="Gaussian blur radius for background")
    replace_color_rgba: Optional[Tuple[int, int, int, int]] = None
    replace_image_path: Optional[Path] = None
    replace_image_url: Optional[str] = None
    feather_radius: float = Field(default=2.0, description="Feather cutout edges")
    subject_scale: float = Field(default=1.0, description="Scale factor for subject when compositing")
    subject_offset_xy: Tuple[int, int] = Field(default=(0, 0), description="dx,dy offset of subject")


class FilterType(str, Enum):
    grayscale = "grayscale"
    sepia = "sepia"
    sharpen = "sharpen"
    gaussian_blur = "gaussian_blur"
    median_blur = "median_blur"
    edge_enhance = "edge_enhance"
    emboss = "emboss"
    brightness = "brightness"
    contrast = "contrast"
    saturation = "saturation"
    hue_shift = "hue_shift"
    gamma = "gamma"
    bilateral = "bilateral"
    clahe = "clahe"
    vignette = "vignette"
    oil_paint = "oil_paint"
    cartoon = "cartoon"
    pencil_sketch = "pencil_sketch"
    color_splash = "color_splash"
    noise_reduction = "noise_reduction"
    invert = "invert"
    posterize = "posterize"
    solarize = "solarize"
    color_balance = "color_balance"
    gradient_map = "gradient_map"
    glitch = "glitch"


class FilterSpec(BaseModel):
    type: FilterType
    amount: Optional[float] = Field(default=None, description="Intensity or parameter for the filter")
    color: Optional[Tuple[int, int, int]] = Field(default=None, description="Color parameter for filters that need a color")
    color_mask: Optional[Tuple[int, int, int]] = Field(default=None, description="Color mask for selective color operations")
    threshold: Optional[float] = Field(default=None, description="Threshold value for certain filters")
    radius: Optional[int] = Field(default=None, description="Radius parameter for filters that need it")
    strength: Optional[float] = Field(default=0.5, description="Strength of the filter effect, normalized between 0 and 1")
    preserve_details: Optional[bool] = Field(default=True, description="Whether to preserve details in certain filters")
    gradient_colors: Optional[List[Tuple[int, int, int]]] = Field(default=None, description="Colors for gradient map filter")


class OverlayType(str, Enum):
    image = "image"
    text = "text"


class OverlayItem(BaseModel):
    type: OverlayType
    # Position and size
    x: int = 0
    y: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    rotation_deg: float = 0.0
    blend_mode: str = Field(default="normal", description="normal|multiply|screen|overlay|add|subtract")

    # Image overlay-specific
    image_path: Optional[Path] = None
    image_url: Optional[str] = None

    # Text overlay-specific
    text: Optional[str] = None
    font_size: int = 32
    font_color_rgba: Tuple[int, int, int, int] = (255, 255, 255, 255)
    font_path: Optional[Path] = None


class EraseShapeType(str, Enum):
    rectangle = "rectangle"
    circle = "circle"
    polygon = "polygon"
    brush = "brush"
    smart = "smart"


class EraseShape(BaseModel):
    type: EraseShapeType
    x: int
    y: int
    width: Optional[int] = None
    height: Optional[int] = None
    radius: Optional[int] = None
    blur: bool = False
    blur_radius: float = 8.0
    polygon_points: Optional[List[Tuple[int, int]]] = None
    mosaic: bool = False
    mosaic_block: int = 16
    brush_size: Optional[int] = Field(default=20, description="Size of brush stroke for brush eraser")
    brush_hardness: Optional[float] = Field(default=0.5, description="Hardness of brush edge (0.0-1.0)")
    brush_points: Optional[List[Tuple[int, int]]] = Field(default=None, description="Points for brush stroke path")
    smart_tolerance: Optional[int] = Field(default=30, description="Color tolerance for smart selection")
    smart_contiguous: Optional[bool] = Field(default=True, description="Whether smart selection should be contiguous")


class EffectsInput(BaseModel):
    file_path: Optional[Path] = None
    image_bytes: Optional[bytes] = None
    url: Optional[str] = None


class EffectsOptions(BaseModel):
    background: Optional[BackgroundAction] = None
    filters: List[FilterSpec] = Field(default_factory=list)
    overlays: List[OverlayItem] = Field(default_factory=list)
    erase: List[EraseShape] = Field(default_factory=list)


class EffectsResult(BaseModel):
    output_path: Optional[Path]
    width: int
    height: int
    bytes_written: int
    extra: dict = Field(default_factory=dict)


