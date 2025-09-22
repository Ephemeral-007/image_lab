from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .models.effects_models import (
    EffectsOptions,
    BackgroundAction,
    FilterSpec,
    OverlayItem,
    EraseShape,
    FilterType
)
from .src.result import EffectsAPIResult
from .source import (
    apply_effects,
    apply_background_effect,
    apply_filters,
    apply_single_filter,
    apply_overlays,
    apply_eraser,
    get_available_filters
)

router = APIRouter(prefix="/effects", tags=["Image Effects"])


class EffectsQuery(BaseModel):
    options: EffectsOptions


class BackgroundQuery(BaseModel):
    background: BackgroundAction


class FiltersQuery(BaseModel):
    filters: List[FilterSpec]


class SingleFilterQuery(BaseModel):
    filter: FilterSpec


class OverlaysQuery(BaseModel):
    overlays: List[OverlayItem]


class EraseQuery(BaseModel):
    erase: List[EraseShape]


@router.post("/", response_model=EffectsAPIResult)
async def effects_endpoint(
    query: EffectsQuery,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None
):
    """
    Apply multiple effects to an image.
    
    This endpoint allows combining background effects, filters, overlays, and erasers.
    
    - **query**: JSON with all effect options
    - **file**: Upload an image file
    - **url**: Alternative to file - specify image URL
    
    Returns processed image path and metadata.
    """
    return await apply_effects(query.options, file, url)


@router.post("/background", response_model=EffectsAPIResult)
async def background_endpoint(
    query: BackgroundQuery,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None
):
    """
    Apply background effects to an image.
    
    Options:
    - Remove background (place on white)
    - Make background transparent
    - Blur background
    - Replace background with color
    - Replace background with another image
    """
    return await apply_background_effect(query.background, file, url)


@router.post("/filters", response_model=EffectsAPIResult)
async def filters_endpoint(
    query: FiltersQuery,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None
):
    """
    Apply multiple filters to an image.
    
    Filters are applied in sequence. You can specify parameters for each filter.
    """
    return await apply_filters(query.filters, file, url)


@router.post("/filter", response_model=EffectsAPIResult)
async def filter_endpoint(
    query: SingleFilterQuery,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None
):
    """
    Apply a single filter to an image.
    
    Simplified endpoint for applying just one filter with its parameters.
    """
    return await apply_single_filter(query.filter, file, url)


@router.post("/overlays", response_model=EffectsAPIResult)
async def overlays_endpoint(
    query: OverlaysQuery,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None
):
    """
    Add overlays to an image.
    
    Overlay types:
    - Image overlays (from file or URL)
    - Text overlays with font customization
    """
    return await apply_overlays(query.overlays, file, url)


@router.post("/erase", response_model=EffectsAPIResult)
async def erase_endpoint(
    query: EraseQuery,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None
):
    """
    Erase portions of an image.
    
    Eraser shapes:
    - Rectangle
    - Circle
    - Polygon
    - Brush
    - Smart selection
    
    Options for feathering edges and applying mosaic instead of transparency.
    """
    return await apply_eraser(query.erase, file, url)


@router.get("/filters/available")
async def available_filters_endpoint():
    """
    Get list of all available filters.
    
    Returns two lists:
    - all_filters: All filter types defined in the system
    - available_filters: Filters currently available/registered with the factory
    """
    return get_available_filters()


# Form-based simplified endpoints

@router.post("/filter/simple", response_model=EffectsAPIResult)
async def simple_filter_endpoint(
    filter_type: FilterType = Form(...),
    amount: Optional[float] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None
):
    """
    Simple form-based filter endpoint.
    
    Apply a single filter using form fields instead of JSON.
    Useful for simple integrations and testing.
    """
    filter_spec = FilterSpec(type=filter_type, amount=amount)
    return await apply_single_filter(filter_spec, file, url)


@router.post("/background/simple", response_model=EffectsAPIResult)
async def simple_background_endpoint(
    action: str = Form(...),
    blur_radius: Optional[float] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None
):
    """
    Simple form-based background effect endpoint.
    
    Apply background effects using form fields instead of JSON.
    Supports basic background operations.
    """
    try:
        background = BackgroundAction(action=action)
        if blur_radius is not None:
            background.blur_radius = blur_radius
        return await apply_background_effect(background, file, url)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid action: {action}. Valid options: remove, transparent, blur, replace_color, replace_image"
        )
