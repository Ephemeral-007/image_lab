from __future__ import annotations

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
    FilterType,
    OverlayItem,
    OverlayType,
)


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
    if spec.type == FilterType.grayscale:
        return image.convert("L").convert("RGBA")
    if spec.type == FilterType.sepia:
        img = image.convert("RGB")
        np_img = np.array(img, dtype=np.float32)
        tr = 0.393 * np_img[:, :, 0] + 0.769 * np_img[:, :, 1] + 0.189 * np_img[:, :, 2]
        tg = 0.349 * np_img[:, :, 0] + 0.686 * np_img[:, :, 1] + 0.168 * np_img[:, :, 2]
        tb = 0.272 * np_img[:, :, 0] + 0.534 * np_img[:, :, 1] + 0.131 * np_img[:, :, 2]
        sep = np.stack([tr, tg, tb], axis=2)
        sep = np.clip(sep, 0, 255).astype(np.uint8)
        return Image.fromarray(sep, mode="RGB").convert("RGBA")
    if spec.type == FilterType.sharpen:
        return image.filter(ImageFilter.UnsharpMask(radius=2, percent=150))
    if spec.type == FilterType.gaussian_blur:
        return image.filter(ImageFilter.GaussianBlur(radius=spec.amount or 2.0))
    if spec.type == FilterType.median_blur:
        return image.filter(ImageFilter.MedianFilter(size=int(spec.amount or 3)))
    if spec.type == FilterType.edge_enhance:
        return image.filter(ImageFilter.EDGE_ENHANCE_MORE)
    if spec.type == FilterType.emboss:
        return image.filter(ImageFilter.EMBOSS)
    if spec.type == FilterType.brightness:
        return ImageEnhance.Brightness(image).enhance(float(spec.amount or 1.0))
    if spec.type == FilterType.contrast:
        return ImageEnhance.Contrast(image).enhance(float(spec.amount or 1.0))
    if spec.type == FilterType.saturation:
        return ImageEnhance.Color(image).enhance(float(spec.amount or 1.0))
    if spec.type == FilterType.hue_shift:
        # approximate hue shift by rotating RGB channels (simple, research can replace with HSV pipeline)
        amount = int(spec.amount or 0)
        r, g, b, a = image.split()
        return Image.merge("RGBA", (g, b, r, a)) if amount % 3 else image
    if spec.type == FilterType.gamma:
        gamma = max(0.1, float(spec.amount or 1.0))
        inv = 1.0 / gamma
        lut = [min(255, int((i / 255.0) ** inv * 255.0)) for i in range(256)]
        r, g, b, a = image.split()
        r = r.point(lut); g = g.point(lut); b = b.point(lut)
        return Image.merge("RGBA", (r, g, b, a))
    if spec.type == FilterType.bilateral:
        rgb = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        d = 9
        sigma_color = 75
        sigma_space = 75
        out = cv2.bilateralFilter(rgb, d, sigma_color, sigma_space)
        return Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB)).convert("RGBA")
    if spec.type == FilterType.clahe:
        rgb = np.array(image.convert("RGB"))
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=float(spec.amount or 2.0), tileGridSize=(8, 8))
        cl = clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        out = cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)
        return Image.fromarray(out).convert("RGBA")
    if spec.type == FilterType.vignette:
        rgb = np.array(image.convert("RGB"))
        rows, cols = rgb.shape[:2]
        kernel_x = cv2.getGaussianKernel(cols, int(spec.amount or max(cols, rows) / 3))
        kernel_y = cv2.getGaussianKernel(rows, int(spec.amount or max(cols, rows) / 3))
        kernel = kernel_y * kernel_x.T
        mask = kernel / kernel.max()
        out = (rgb * mask[:, :, None]).astype(np.uint8)
        return Image.fromarray(out).convert("RGBA")
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
    canvas = image.copy()
    for sh in shapes:
        mask = Image.new("L", canvas.size, 0)
        mdraw = ImageDraw.Draw(mask)
        if sh.type == EraseShapeType.rectangle and sh.width and sh.height:
            mdraw.rectangle([sh.x, sh.y, sh.x + sh.width, sh.y + sh.height], fill=255)
        elif sh.type == EraseShapeType.circle and sh.radius:
            mdraw.ellipse([sh.x - sh.radius, sh.y - sh.radius, sh.x + sh.radius, sh.y + sh.radius], fill=255)
        if sh.blur:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=sh.blur_radius))
        if sh.mosaic:
            region = Image.composite(canvas, Image.new("RGBA", canvas.size, (0, 0, 0, 0)), mask)
            # apply pixelation to region
            block = max(2, int(sh.mosaic_block))
            small = region.resize((max(1, region.width // block), max(1, region.height // block)), resample=Image.NEAREST)
            pixelated = small.resize(region.size, Image.NEAREST)
            canvas = Image.composite(pixelated, canvas, mask)
        else:
            transparent = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            canvas = Image.composite(transparent, canvas, mask)
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


