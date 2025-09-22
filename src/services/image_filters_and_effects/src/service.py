from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
import cv2  # type: ignore

try:
    from rembg import remove as rembg_remove  # type: ignore
    _HAS_REMBG = True
except Exception:
    _HAS_REMBG = False

from ..models.effects_models import (
    BackgroundAction,
    BackgroundActionType,
    EffectsInput,
    EffectsOptions,
    EffectsResult,
    EraseShape,
    EraseShapeType,
    FilterSpec,
    OverlayItem,
    OverlayType,
)

# Configure logging
logger = logging.getLogger(__name__)


def _load_image(effects_input: EffectsInput) -> Image.Image:
    if effects_input.file_path is not None:
        return Image.open(str(effects_input.file_path))
    if effects_input.image_bytes is not None:
        return Image.open(BytesIO(effects_input.image_bytes))
    if effects_input.url is not None:
        with httpx.Client(timeout=30) as client:
            resp = client.get(effects_input.url)
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content))
    raise ValueError("Provide file_path, image_bytes, or url")


def _ensure_rgba(image: Image.Image) -> Image.Image:
    return image.convert("RGBA") if image.mode != "RGBA" else image


def _feather_alpha(mask: Image.Image, radius: float) -> Image.Image:
    if radius <= 0:
        return mask
    return mask.filter(ImageFilter.GaussianBlur(radius=radius))


def _apply_background(image: Image.Image, bg: BackgroundAction) -> Image.Image:
    base = _ensure_rgba(image)
    if bg.action in {BackgroundActionType.remove, BackgroundActionType.transparent}:
        if _HAS_REMBG:
            cut = rembg_remove(np.array(base))
            cutout = Image.open(BytesIO(cut)).convert("RGBA")
            # Optional feathering
            if "A" in cutout.getbands():
                a = cutout.split()[-1]
                a = _feather_alpha(a, bg.feather_radius)
                cutout.putalpha(a)
        else:
            # Fallback: simple alpha mask by thresholding edges (not as accurate)
            cutout = base
        if bg.action == BackgroundActionType.transparent:
            return cutout
        # Remove background -> place subject over solid white
        canvas = Image.new("RGBA", base.size, (255, 255, 255, 255))
        if bg.subject_scale != 1.0:
            new_w = max(1, int(cutout.width * bg.subject_scale))
            new_h = max(1, int(cutout.height * bg.subject_scale))
            cutout = cutout.resize((new_w, new_h), resample=Image.LANCZOS)
        dx, dy = bg.subject_offset_xy
        canvas.alpha_composite(cutout)
        return canvas
    if bg.action == BackgroundActionType.blur:
        if _HAS_REMBG:
            cutout = Image.open(BytesIO(rembg_remove(np.array(base)))).convert("RGBA")
            # Build blurred background from original
            blurred = base.filter(ImageFilter.GaussianBlur(radius=bg.blur_radius or 12.0))
            if bg.subject_scale != 1.0:
                new_w = max(1, int(cutout.width * bg.subject_scale))
                new_h = max(1, int(cutout.height * bg.subject_scale))
                cutout = cutout.resize((new_w, new_h), resample=Image.LANCZOS)
            dx, dy = bg.subject_offset_xy
            blurred.alpha_composite(cutout, dest=(dx, dy))
            return blurred
        return base.filter(ImageFilter.GaussianBlur(radius=bg.blur_radius or 12.0))
    if bg.action == BackgroundActionType.replace_color:
        color = bg.replace_color_rgba or (255, 255, 255, 255)
        if _HAS_REMBG:
            cutout = Image.open(BytesIO(rembg_remove(np.array(base)))).convert("RGBA")
            canvas = Image.new("RGBA", base.size, color)
            if bg.subject_scale != 1.0:
                new_w = max(1, int(cutout.width * bg.subject_scale))
                new_h = max(1, int(cutout.height * bg.subject_scale))
                cutout = cutout.resize((new_w, new_h), resample=Image.LANCZOS)
            dx, dy = bg.subject_offset_xy
            canvas.alpha_composite(cutout, dest=(dx, dy))
            return canvas
        return Image.new("RGBA", base.size, color)
    if bg.action == BackgroundActionType.replace_image:
        # load replacement image
        rep = None
        if bg.replace_image_path is not None:
            rep = Image.open(str(bg.replace_image_path)).convert("RGBA")
        elif bg.replace_image_url is not None:
            with httpx.Client(timeout=30) as client:
                r = client.get(bg.replace_image_url)
                r.raise_for_status()
                rep = Image.open(BytesIO(r.content)).convert("RGBA")
        if rep is None:
            return base
        rep = rep.resize(base.size, resample=Image.LANCZOS)
        if _HAS_REMBG:
            cutout = Image.open(BytesIO(rembg_remove(np.array(base)))).convert("RGBA")
            if bg.subject_scale != 1.0:
                new_w = max(1, int(cutout.width * bg.subject_scale))
                new_h = max(1, int(cutout.height * bg.subject_scale))
                cutout = cutout.resize((new_w, new_h), resample=Image.LANCZOS)
            dx, dy = bg.subject_offset_xy
            rep.alpha_composite(cutout, dest=(dx, dy))
            return rep
        return rep
    return base


def _apply_filter(image: Image.Image, spec: FilterSpec) -> Image.Image:
    """Apply a filter to an image using the Strategy Pattern via the FilterFactory."""
    from .filters import FilterFactory
    
    try:
        # Create the appropriate filter strategy using the factory
        filter_strategy = FilterFactory.create(spec)
        
        # Apply the filter using the strategy
        return filter_strategy.apply(image, spec)
    except ValueError as e:
        # If the filter type is not registered, log and return original image
        print(f"Warning: {str(e)}")
        return image
    except Exception as e:
        # For other errors, log and return original image
        print(f"Error applying filter {spec.type}: {str(e)}")
        return image


def _apply_overlays(image: Image.Image, overlays: list[OverlayItem]) -> Image.Image:
    canvas = image.copy()
    for ov in overlays:
        if ov.type == OverlayType.image:
            src = None
            if ov.image_path is not None:
                src = Image.open(str(ov.image_path)).convert("RGBA")
            elif ov.image_url is not None:
                with httpx.Client(timeout=30) as client:
                    resp = client.get(ov.image_url)
                    resp.raise_for_status()
                    src = Image.open(BytesIO(resp.content)).convert("RGBA")
            if src is None:
                continue
            if ov.width and ov.height:
                src = src.resize((ov.width, ov.height), resample=Image.LANCZOS)
            if ov.rotation_deg:
                src = src.rotate(ov.rotation_deg, expand=True)
            if ov.opacity < 1.0:
                alpha = src.split()[-1].point(lambda p: int(p * ov.opacity))
                src.putalpha(alpha)
            if ov.blend_mode == "normal":
                canvas.alpha_composite(src, (ov.x, ov.y))
            else:
                base = canvas.copy()
                temp = Image.new("RGBA", base.size, (0, 0, 0, 0))
                temp.alpha_composite(src, (ov.x, ov.y))
                # convert to numpy for blend modes
                A = np.array(base).astype(np.float32) / 255.0
                B = np.array(temp).astype(np.float32) / 255.0
                def blend(a, b, mode):
                    if mode == "multiply":
                        return a * b
                    if mode == "screen":
                        return 1 - (1 - a) * (1 - b)
                    if mode == "overlay":
                        return np.where(a < 0.5, 2 * a * b, 1 - 2 * (1 - a) * (1 - b))
                    if mode == "add":
                        return np.clip(a + b, 0, 1)
                    if mode == "subtract":
                        return np.clip(a - b, 0, 1)
                    return b
                rgb_a, alpha_a = A[..., :3], A[..., 3:4]
                rgb_b, alpha_b = B[..., :3], B[..., 3:4]
                rgb = blend(rgb_a, rgb_b, ov.blend_mode)
                alpha = np.clip(alpha_a + alpha_b - alpha_a * alpha_b, 0, 1)
                C = np.concatenate([rgb, alpha], axis=2)
                canvas = Image.fromarray((C * 255).astype(np.uint8), mode="RGBA")
        else:
            draw = ImageDraw.Draw(canvas)
            try:
                font = ImageFont.truetype(str(ov.font_path), size=ov.font_size) if ov.font_path else ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            draw.text((ov.x, ov.y), ov.text or "", fill=ov.font_color_rgba, font=font)
    return canvas


def _apply_eraser(image: Image.Image, shapes: list[EraseShape]) -> Image.Image:
    """Apply eraser effects to an image.
    
    Uses the enhanced eraser functionality from eraser_utils module.
    """
    from .erasers.eraser_utils import create_eraser_mask, apply_eraser
    
    canvas = image.copy()
    for sh in shapes:
        try:
            # Create mask based on shape type
            mask = create_eraser_mask(canvas, sh)
            
            # Apply eraser using the mask
            canvas = apply_eraser(canvas, mask, sh.mosaic, sh.mosaic_block)
        except Exception as e:
            # Log any errors and continue with next shape
            print(f"Error applying eraser shape {sh.type}: {str(e)}")
            continue
            
    return canvas


class ImageEffectsService:
    def apply(self, effects_input: EffectsInput, options: EffectsOptions, output_path: Optional[Path] = None) -> EffectsResult:
        img = _load_image(effects_input).convert("RGBA")
        w, h = img.size
        out = img

        if options.background is not None:
            out = _apply_background(out, options.background)

        for f in options.filters:
            out = _apply_filter(out, f)

        if options.overlays:
            out = _apply_overlays(out, options.overlays)

        if options.erase:
            out = _apply_eraser(out, options.erase)

        final_output_path = output_path or (Path("./effects") / "output.png")
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
        out.save(final_output_path, format="PNG")

        return EffectsResult(
            output_path=final_output_path,
            width=w,
            height=h,
            bytes_written=final_output_path.stat().st_size,
            extra={"rembg": str(_HAS_REMBG)},
        )


