from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import httpx
import numpy as np
from PIL import Image, ImageOps
from skimage.metrics import structural_similarity as ssim

from ..models.resizer_models import (
    DimensionOptions,
    OutputFormat,
    ResizerInput,
    ResizerOptions,
    ResizerResult,
)


def _load_image(resizer_input: ResizerInput) -> Image.Image:
    if resizer_input.file_path is not None:
        return Image.open(str(resizer_input.file_path))
    if resizer_input.image_bytes is not None:
        return Image.open(BytesIO(resizer_input.image_bytes))
    if resizer_input.url is not None:
        with httpx.Client(timeout=30) as client:
            resp = client.get(resizer_input.url)
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content))
    raise ValueError("Provide file_path, image_bytes, or url")


def _normalize_to_rgb(image: Image.Image, background_rgba: Tuple[int, int, int, int]) -> Image.Image:
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        bg = Image.new("RGBA", image.size, background_rgba)
        return Image.alpha_composite(bg, image.convert("RGBA")).convert("RGB")
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _resize(image: Image.Image, dims: DimensionOptions | None) -> Image.Image:
    if dims is None:
        return image
    w, h = image.size
    target_w = dims.width or w
    target_h = dims.height or h
    if not dims.allow_upscale:
        target_w = min(target_w, w)
        target_h = min(target_h, h)
    if dims.strategy.value == "fit_within":
        return ImageOps.contain(image, (target_w, target_h), method=Image.LANCZOS)
    if dims.strategy.value == "fill_and_crop":
        return ImageOps.fit(image, (target_w, target_h), method=Image.LANCZOS, centering=(0.5, 0.5))
    return image.resize((target_w, target_h), resample=Image.LANCZOS)


def _save_with_quality(image: Image.Image, fmt: OutputFormat, quality: int, keep_metadata: bool) -> bytes:
    params = {}
    if fmt in {OutputFormat.jpeg, OutputFormat.jpg}:
        params.update({"format": "JPEG", "optimize": True, "progressive": True, "quality": quality})
        if keep_metadata and "exif" in image.info and image.info["exif"]:
            params["exif"] = image.info["exif"]
    elif fmt == OutputFormat.webp:
        params.update({"format": "WEBP", "quality": quality, "method": 6})
    elif fmt == OutputFormat.png:
        # PNG compression is not quality-based; use adaptive palette for size
        params.update({"format": "PNG", "optimize": True})
    else:
        params.update({"format": fmt.value.upper()})

    buf = BytesIO()
    image.save(buf, **params)
    return buf.getvalue()


def _compute_metrics(original_rgb: Image.Image, candidate_bytes: bytes) -> tuple[float, float]:
    cand = Image.open(BytesIO(candidate_bytes)).convert("RGB")
    a = np.asarray(original_rgb, dtype=np.float32)
    b = np.asarray(cand, dtype=np.float32)
    mse = np.mean((a - b) ** 2)
    if mse == 0:
        psnr = 100.0
    else:
        psnr = 20 * np.log10(255.0 / np.sqrt(mse))
    return psnr, ssim(a, b, channel_axis=2, data_range=255)


class ImageResizerService:
    def resize(self, resizer_input: ResizerInput, options: ResizerOptions, output_path: Optional[Path] = None) -> ResizerResult:
        img = _load_image(resizer_input)
        img.load()
        img = ImageOps.exif_transpose(img)
        rgb = _normalize_to_rgb(img, options.background_rgba)
        resized = _resize(rgb, options.dimensions)

        # Choose output format
        fmt = options.output_format or OutputFormat.jpeg

        # If target size specified, binary search quality and possibly format
        candidate_bytes: bytes
        psnr_val: Optional[float] = None
        ssim_val: Optional[float] = None

        if options.target_size is not None:
            target = options.target_size
            best_bytes = None
            best_quality = None
            best_fmt = None
            for fmt_choice in target.format_priority:
                low, high = target.quality_min, target.quality_max
                for _ in range(target.max_iterations):
                    q = (low + high) // 2
                    cand = _save_with_quality(resized, fmt_choice, q, options.keep_metadata)
                    size_kb = len(cand) // 1024
                    # Check SSIM threshold
                    if target.ssim_threshold is not None:
                        psnr_c, ssim_c = _compute_metrics(rgb, cand)
                        if ssim_c < target.ssim_threshold:
                            # Too low quality -> increase quality
                            low = q + 1
                            continue
                    if size_kb > target.target_size_kb + target.tolerance_kb:
                        # Too big -> decrease quality
                        high = q - 1
                    elif size_kb < target.target_size_kb - target.tolerance_kb:
                        # Too small -> increase quality (to hit size window with higher quality)
                        low = q + 1
                        best_bytes = cand
                        best_quality = q
                        best_fmt = fmt_choice
                    else:
                        # In window
                        best_bytes = cand
                        best_quality = q
                        best_fmt = fmt_choice
                        break
                if best_bytes is not None:
                    break

            if best_bytes is None:
                # Fallback: save once with mid quality in first format
                fmt_choice = target.format_priority[0]
                best_quality = (target.quality_min + target.quality_max) // 2
                best_bytes = _save_with_quality(resized, fmt_choice, best_quality, options.keep_metadata)
                best_fmt = fmt_choice

            candidate_bytes = best_bytes
            fmt = best_fmt
            psnr_val, ssim_val = _compute_metrics(rgb, candidate_bytes)
        else:
            q_default = 85
            candidate_bytes = _save_with_quality(resized, fmt, q_default, options.keep_metadata)
            psnr_val, ssim_val = _compute_metrics(rgb, candidate_bytes)

        final_output_path = output_path or (Path("./resized") / "output.jpg")
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
        if final_output_path.suffix.lower() not in (f".{fmt.value}", ".jpg" if fmt in {OutputFormat.jpeg, OutputFormat.jpg} else f".{fmt.value}"):
            ext = ".jpg" if fmt in {OutputFormat.jpeg, OutputFormat.jpg} else f".{fmt.value}"
            final_output_path = final_output_path.with_suffix(ext)
        final_output_path.write_bytes(candidate_bytes)

        width, height = resized.size
        return ResizerResult(
            output_path=final_output_path,
            output_format=fmt,
            width=width,
            height=height,
            bytes_written=final_output_path.stat().st_size,
            psnr=psnr_val,
            ssim=ssim_val,
        )


