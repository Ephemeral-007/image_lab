from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

import httpx
from fastapi import HTTPException, UploadFile

from .models.effects_models import (
    EffectsInput, 
    EffectsOptions, 
    EffectsResult,
    BackgroundAction,
    FilterSpec,
    OverlayItem,
    EraseShape
)
from .src.service import ImageEffectsService
from .src.result import EffectsAPIResult

# Configure logging
logger = logging.getLogger(__name__)
effects_service = ImageEffectsService()


async def process_input_file(
    file: Optional[UploadFile] = None, 
    url: Optional[str] = None
) -> tuple[EffectsInput, str]:
    """
    Process input file from either uploaded file or URL.
    
    Args:
        file: The uploaded file
        url: URL to an image
        
    Returns:
        Tuple of (EffectsInput, filename)
        
    Raises:
        HTTPException: If neither file nor URL is provided
    """
    if file is not None:
        content = await file.read()
        eff_input = EffectsInput(image_bytes=content)
        filename = file.filename or "output.png"
    elif url is not None:
        eff_input = EffectsInput(url=url)
        filename = "output.png"
    else:
        raise HTTPException(status_code=400, detail="Provide either file or url")
    
    return eff_input, filename


async def apply_effects(
    options: EffectsOptions,
    file: Optional[UploadFile] = None,
    url: Optional[str] = None,
    output_filename: Optional[str] = None
) -> EffectsAPIResult:
    """
    Apply effects to an image.
    
    Args:
        options: The effects options
        file: The uploaded file
        url: URL to an image
        output_filename: Custom output filename
        
    Returns:
        EffectsAPIResult with processing results
        
    Raises:
        HTTPException: On processing errors
    """
    try:
        eff_input, filename = await process_input_file(file, url)
        
        if output_filename:
            filename = output_filename
        
        out_dir = Path("./effects")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / filename
        
        result = effects_service.apply(eff_input, options, output_path=output_path)
        
        return EffectsAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            width=result.width,
            height=result.height,
            bytes_written=result.bytes_written,
            extra=result.extra,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error applying effects")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def apply_background_effect(
    background: BackgroundAction,
    file: Optional[UploadFile] = None,
    url: Optional[str] = None
) -> EffectsAPIResult:
    """Apply background effects to an image."""
    options = EffectsOptions(background=background)
    return await apply_effects(options, file, url, "background_effect.png")


async def apply_filters(
    filters: list[FilterSpec],
    file: Optional[UploadFile] = None,
    url: Optional[str] = None
) -> EffectsAPIResult:
    """Apply multiple filters to an image."""
    options = EffectsOptions(filters=filters)
    return await apply_effects(options, file, url, "filtered.png")


async def apply_single_filter(
    filter_spec: FilterSpec,
    file: Optional[UploadFile] = None,
    url: Optional[str] = None
) -> EffectsAPIResult:
    """Apply a single filter to an image."""
    options = EffectsOptions(filters=[filter_spec])
    filename = f"{filter_spec.type}_filtered.png"
    return await apply_effects(options, file, url, filename)


async def apply_overlays(
    overlays: list[OverlayItem],
    file: Optional[UploadFile] = None,
    url: Optional[str] = None
) -> EffectsAPIResult:
    """Apply overlays to an image."""
    options = EffectsOptions(overlays=overlays)
    return await apply_effects(options, file, url, "overlaid.png")


async def apply_eraser(
    erase: list[EraseShape],
    file: Optional[UploadFile] = None,
    url: Optional[str] = None
) -> EffectsAPIResult:
    """Apply eraser to an image."""
    options = EffectsOptions(erase=erase)
    return await apply_effects(options, file, url, "erased.png")


def get_available_filters() -> dict:
    """Get list of all available filters."""
    from .models.effects_models import FilterType
    basic_filters = [f for f in FilterType.__members__]
    
    try:
        # Check which advanced filters are available in the system
        from .src.filters import FilterFactory
        available_filters = [filter_type for filter_type in FilterType.__members__ 
                          if FilterFactory.is_registered(FilterType(filter_type))]
        
        return {
            "all_filters": basic_filters,
            "available_filters": available_filters
        }
    except ImportError:
        # Fallback if FilterFactory is not accessible
        return {
            "all_filters": basic_filters
        }
