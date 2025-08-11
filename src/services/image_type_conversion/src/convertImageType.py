from __future__ import annotations

from pathlib import Path
from io import BytesIO
from typing import List, Optional, Tuple

from PIL import Image

from ..models.conversion_models import AdvancedConversionOptions, BatchConversionRequest, ConversionInput, ConversionOptions, ConversionResult, ResizeOptions, TargetImageFormat
from ..utils.pillow_utils import build_save_params, convert_to_srgb, extract_metadata_info, is_animated, normalize_mode_for_target, quantize_image, resize_image, save_image_bytes
from skimage.metrics import structural_similarity as ssim
import numpy as np


class ConvertImageType:
    def __init__(self):
        pass

    def _load_image(self, conv_input: ConversionInput) -> Image.Image:
        if conv_input.file_path is not None:
            return Image.open(str(conv_input.file_path))
        if conv_input.image_bytes is not None:
            from io import BytesIO

            return Image.open(BytesIO(conv_input.image_bytes))
        if conv_input.url is not None:
            import httpx

            with httpx.Client(timeout=30) as client:
                resp = client.get(conv_input.url)
                resp.raise_for_status()
                from io import BytesIO

                return Image.open(BytesIO(resp.content))
        raise ValueError("No valid input provided: file_path, image_bytes, or url required")

    def convert(
        self,
        conv_input: ConversionInput,
        options: ConversionOptions,
        output_path: Optional[Path] = None,
    ) -> ConversionResult:
        image = self._load_image(conv_input)
        image.load()

        # Gather source info
        original_w, original_h = image.size
        animated = is_animated(image)

        # Normalize according to target
        normalized = normalize_mode_for_target(
            image=image,
            target_format=options.to_format.value,
            background_rgba=options.background_color or (255, 255, 255, 255),
        )

        # Advanced pipeline steps if provided
        if isinstance(options, AdvancedConversionOptions):
            # Color management
            if options.color_profile_action == options.color_profile_action.convert_to_srgb:
                normalized = convert_to_srgb(normalized, assign_only=False)
            elif options.color_profile_action == options.color_profile_action.assign_srgb:
                normalized = convert_to_srgb(normalized, assign_only=True)

            # Resize
            if options.resize is not None:
                normalized = resize_image(
                    normalized,
                    max_w=options.resize.max_width,
                    max_h=options.resize.max_height,
                    strategy=options.resize.strategy.value,
                    allow_upscale=options.resize.allow_upscale,
                )

            # Quantize
            if options.quantize is not None:
                normalized = quantize_image(
                    normalized,
                    num_colors=options.quantize.num_colors,
                    dither=options.quantize.dither,
                )

        save_params = build_save_params(
            target_format=options.to_format.value,
            quality=options.quality,
            optimize=options.optimize,
            progressive=options.progressive,
            keep_metadata=options.keep_metadata,
            dpi=options.dpi,
            lossless_webp=options.lossless_webp,
            png_compress_level=options.png_compress_level,
        )

        # Preserve EXIF/ICC where possible
        if options.keep_metadata:
            if "exif" in image.info and image.info["exif"]:
                save_params.setdefault("exif", image.info["exif"])
            if "icc_profile" in image.info and image.info["icc_profile"]:
                save_params.setdefault("icc_profile", image.info["icc_profile"])

        data = save_image_bytes(
            image=normalized,
            target_format=options.to_format.value,
            save_params=save_params,
            keep_animation=bool(options.keep_animation),
        )

        bytes_written: Optional[int] = None
        final_output_path: Optional[Path] = None
        if output_path is not None:
            final_output_path = Path(output_path)
            # Ensure suffix matches target format (normalize jpg->jpeg)
            suffix = ".jpg" if options.to_format in {TargetImageFormat.jpg, TargetImageFormat.jpeg} else f".{options.to_format.value}"
            if final_output_path.suffix.lower() != suffix:
                final_output_path = final_output_path.with_suffix(suffix)
            final_output_path.parent.mkdir(parents=True, exist_ok=True)
            final_output_path.write_bytes(data)
            bytes_written = final_output_path.stat().st_size

        meta_info = extract_metadata_info(image)

        result = ConversionResult(
            output_path=final_output_path,
            output_format=options.to_format,
            width=normalized.width,
            height=normalized.height,
            num_frames=getattr(image, "n_frames", 1) if animated else 1,
            was_animated=animated,
            metadata_preserved=options.keep_metadata and bool(meta_info),
            bytes_written=bytes_written,
            extra={"source_mode": image.mode, **meta_info},
        )

        # Optional metrics: PSNR and SSIM comparing source->converted (if options.compute_metrics)
        if isinstance(options, AdvancedConversionOptions) and options.compute_metrics:
            try:
                # Only compute on first frame and RGB
                src = image.convert("RGB")
                dst = Image.open(BytesIO(data)).convert("RGB")
                src_np = np.asarray(src, dtype=np.float32)
                dst_np = np.asarray(dst, dtype=np.float32)

                mse = np.mean((src_np - dst_np) ** 2)
                if mse == 0:
                    psnr = 100.0
                else:
                    PIXEL_MAX = 255.0
                    psnr = 20 * np.log10(PIXEL_MAX / np.sqrt(mse))
                ssim_val = ssim(src_np, dst_np, channel_axis=2, data_range=255)
                result.extra.update({"psnr": f"{psnr:.2f}", "ssim": f"{ssim_val:.4f}"})
            except Exception:
                pass

        return result

    def batch_convert(self, request: BatchConversionRequest, output_dir: Path) -> List[ConversionResult]:
        output_dir.mkdir(parents=True, exist_ok=True)
        results: List[ConversionResult] = []
        for idx, target in enumerate(request.targets):
            conv_input = ConversionInput(file_path=request.file_path, image_bytes=request.image_bytes, url=request.url)
            out_path = output_dir / f"output_{idx}.{ 'jpg' if target.to_format.value in ('jpg','jpeg') else target.to_format.value }"
            results.append(self.convert(conv_input, target, out_path))
        return results
