from __future__ import annotations

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from ...models.effects_models import FilterSpec, FilterType
from .base import FilterStrategy
from .factory import FilterFactory


class GrayscaleFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        return image.convert("L").convert("RGBA")
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.grayscale.value


class SepiaFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        img = image.convert("RGB")
        np_img = np.array(img, dtype=np.float32)
        tr = 0.393 * np_img[:, :, 0] + 0.769 * np_img[:, :, 1] + 0.189 * np_img[:, :, 2]
        tg = 0.349 * np_img[:, :, 0] + 0.686 * np_img[:, :, 1] + 0.168 * np_img[:, :, 2]
        tb = 0.272 * np_img[:, :, 0] + 0.534 * np_img[:, :, 1] + 0.131 * np_img[:, :, 2]
        sep = np.stack([tr, tg, tb], axis=2)
        sep = np.clip(sep, 0, 255).astype(np.uint8)
        return Image.fromarray(sep, mode="RGB").convert("RGBA")
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.sepia.value


class SharpenFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        return image.filter(ImageFilter.UnsharpMask(
            radius=spec.radius or 2,
            percent=spec.amount * 150 if spec.amount else 150
        ))
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.sharpen.value


class GaussianBlurFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        return image.filter(ImageFilter.GaussianBlur(radius=spec.amount or 2.0))
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.gaussian_blur.value


class MedianBlurFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        return image.filter(ImageFilter.MedianFilter(size=int(spec.amount or 3)))
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.median_blur.value


class EdgeEnhanceFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        return image.filter(ImageFilter.EDGE_ENHANCE_MORE)
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.edge_enhance.value


class EmbossFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        return image.filter(ImageFilter.EMBOSS)
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.emboss.value


class BrightnessFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        return ImageEnhance.Brightness(image).enhance(float(spec.amount or 1.0))
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.brightness.value


class ContrastFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        return ImageEnhance.Contrast(image).enhance(float(spec.amount or 1.0))
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.contrast.value


class SaturationFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        return ImageEnhance.Color(image).enhance(float(spec.amount or 1.0))
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.saturation.value


class HueShiftFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        amount = int(spec.amount or 0)
        r, g, b, a = image.split()
        return Image.merge("RGBA", (g, b, r, a)) if amount % 3 else image
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.hue_shift.value


class InvertFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        if image.mode == "RGBA":
            r, g, b, a = image.split()
            r = ImageOps.invert(r)
            g = ImageOps.invert(g)
            b = ImageOps.invert(b)
            return Image.merge("RGBA", (r, g, b, a))
        else:
            rgb = image.convert("RGB")
            inverted = ImageOps.invert(rgb)
            return inverted.convert("RGBA")
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.invert.value


# Register all filters with the factory
FilterFactory.register(GrayscaleFilter)
FilterFactory.register(SepiaFilter)
FilterFactory.register(SharpenFilter)
FilterFactory.register(GaussianBlurFilter)
FilterFactory.register(MedianBlurFilter)
FilterFactory.register(EdgeEnhanceFilter)
FilterFactory.register(EmbossFilter)
FilterFactory.register(BrightnessFilter)
FilterFactory.register(ContrastFilter)
FilterFactory.register(SaturationFilter)
FilterFactory.register(HueShiftFilter)
FilterFactory.register(InvertFilter)
