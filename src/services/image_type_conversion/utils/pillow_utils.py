from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image, ImageOps, ImageSequence, ImageCms


def normalize_mode_for_target(image: Image.Image, target_format: str, background_rgba: Tuple[int, int, int, int]) -> Image.Image:
    fmt = target_format.lower()

    # GIF/WEBP may support animation and palette
    if fmt in {"gif"}:
        if image.mode not in ("P", "L"):
            return image.convert("P", palette=Image.ADAPTIVE)
        return image

    if fmt in {"jpeg", "jpg"}:
        # JPEG does not support alpha, flatten on background
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            background = Image.new("RGBA", image.size, background_rgba)
            return Image.alpha_composite(background, image.convert("RGBA")).convert("RGB")
        if image.mode not in ("RGB",):
            return image.convert("RGB")
        return image

    if fmt in {"png", "webp", "tiff", "bmp", "jp2"}:
        # Preserve alpha where possible
        if image.mode in {"1", "L", "P"}:
            return image.convert("RGBA") if "transparency" in image.info else image.convert("RGB")
        return image

    if fmt in {"pdf"}:
        # PDF pages assume RGB
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            background = Image.new("RGBA", image.size, background_rgba)
            return Image.alpha_composite(background, image.convert("RGBA")).convert("RGB")
        if image.mode != "RGB":
            return image.convert("RGB")
        return image

    return image


def build_save_params(
    target_format: str,
    quality: Optional[int] = None,
    optimize: bool = True,
    progressive: bool = True,
    keep_metadata: bool = True,
    dpi: Optional[Tuple[int, int]] = None,
    lossless_webp: Optional[bool] = None,
    png_compress_level: Optional[int] = None,
) -> Dict:
    fmt = target_format.lower()
    params: Dict = {}

    if quality is not None and fmt in {"jpeg", "jpg", "webp", "jp2"}:
        params["quality"] = max(1, min(100, int(quality)))

    if fmt in {"jpeg", "jpg"}:
        params["optimize"] = bool(optimize)
        params["progressive"] = bool(progressive)

    if fmt == "webp":
        if lossless_webp is True:
            params["lossless"] = True
        else:
            params["method"] = 6  # better compression

    if fmt == "png" and png_compress_level is not None:
        params["compress_level"] = max(0, min(9, int(png_compress_level)))

    if dpi is not None:
        params["dpi"] = dpi

    if not keep_metadata:
        params["exif"] = None
        params["icc_profile"] = None

    return params


def extract_metadata_info(image: Image.Image) -> Dict[str, str]:
    info: Dict[str, str] = {}
    if "exif" in image.info and image.info["exif"]:
        info["exif"] = "present"
    if "icc_profile" in image.info and image.info["icc_profile"]:
        info["icc_profile"] = "present"
    return info


def is_animated(image: Image.Image) -> bool:
    return getattr(image, "is_animated", False) and getattr(image, "n_frames", 1) > 1


def save_image_bytes(image: Image.Image, target_format: str, save_params: Dict, keep_animation: bool) -> bytes:
    buffer = BytesIO()
    fmt = target_format.upper()

    if keep_animation and is_animated(image) and fmt in {"GIF", "WEBP"}:
        frames = [frame.copy() for frame in ImageSequence.Iterator(image)]
        duration = image.info.get("duration")
        loop = image.info.get("loop", 0)
        frames[0].save(
            buffer,
            format=fmt,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=loop,
            **save_params,
        )
    else:
        image.save(buffer, format=fmt, **save_params)

    return buffer.getvalue()


def resize_image(image: Image.Image, max_w: Optional[int], max_h: Optional[int], strategy: str, allow_upscale: bool) -> Image.Image:
    if max_w is None and max_h is None:
        return image
    w, h = image.size
    target_w = max_w or w
    target_h = max_h or h
    if not allow_upscale:
        target_w = min(target_w, w)
        target_h = min(target_h, h)

    if strategy == "fit_within":
        img = ImageOps.contain(image, (target_w, target_h), method=Image.LANCZOS)
    elif strategy == "fill_and_crop":
        img = ImageOps.fit(image, (target_w, target_h), method=Image.LANCZOS, centering=(0.5, 0.5))
    else:  # stretch
        img = image.resize((target_w, target_h), resample=Image.LANCZOS)
    return img


def quantize_image(image: Image.Image, num_colors: Optional[int], dither: bool) -> Image.Image:
    if num_colors is None:
        return image
    dither_flag = Image.FLOYDSTEINBERG if dither else Image.NONE
    return image.convert("P", palette=Image.ADAPTIVE, colors=max(2, min(256, num_colors)), dither=dither_flag)


def convert_to_srgb(image: Image.Image, assign_only: bool = False) -> Image.Image:
    try:
        srgb = ImageCms.createProfile("sRGB")
        if "icc_profile" in image.info and image.info["icc_profile"] and not assign_only:
            src = ImageCms.ImageCmsProfile(BytesIO(image.info["icc_profile"]))
            return ImageCms.profileToProfile(image, src, srgb, outputMode=image.mode)
        # Assign sRGB profile without conversion
        out = image.copy()
        out.info["icc_profile"] = ImageCms.ProfileToProfileBytes(srgb)
        return out
    except Exception:
        return image


