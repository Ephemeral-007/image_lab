from __future__ import annotations

import random
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

from ...models.effects_models import FilterSpec, FilterType
from .base import FilterStrategy
from .factory import FilterFactory


class OilPaintFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        # Convert PIL to OpenCV
        cv_img = cv2.cvtColor(np.array(image.convert('RGB')), cv2.COLOR_RGB2BGR)
        
        # Parameters
        radius = spec.radius or 4
        intensity = int(10 * (spec.strength or 0.5)) if spec.strength is not None else 5
        
        # Apply oil paint effect
        oil_img = cv2.xphoto.oilPainting(cv_img, radius, intensity)
        
        # Convert back to PIL
        result = Image.fromarray(cv2.cvtColor(oil_img, cv2.COLOR_BGR2RGB)).convert('RGBA')
        
        # Preserve original alpha channel if available
        if 'A' in image.getbands():
            result.putalpha(image.split()[3])
            
        return result
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.oil_paint.value


class CartoonFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        # Convert PIL to OpenCV
        cv_img = cv2.cvtColor(np.array(image.convert('RGB')), cv2.COLOR_RGB2BGR)
        
        # Parameters
        strength = spec.strength or 0.5
        edge_strength = int(strength * 10) + 1
        
        # Create cartoon effect
        # 1. Apply bilateral filter for smoothing
        color = cv2.bilateralFilter(cv_img, d=9, sigmaColor=250, sigmaSpace=250)
        
        # 2. Convert to grayscale and apply median blur
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 7)
        
        # 3. Create edge mask
        edges = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
            cv2.THRESH_BINARY, 9, edge_strength
        )
        
        # 4. Convert back to RGB
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        # 5. Combine color and edges
        cartoon = cv2.bitwise_and(color, edges)
        
        # Convert back to PIL
        result = Image.fromarray(cv2.cvtColor(cartoon, cv2.COLOR_BGR2RGB)).convert('RGBA')
        
        # Preserve original alpha channel if available
        if 'A' in image.getbands():
            result.putalpha(image.split()[3])
            
        return result
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.cartoon.value


class PencilSketchFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        # Convert PIL to OpenCV
        cv_img = cv2.cvtColor(np.array(image.convert('RGB')), cv2.COLOR_RGB2BGR)
        
        # Parameters 
        sigma_s = 60
        sigma_r = 0.07
        shade_factor = spec.strength or 0.5
        
        # Create pencil sketch effect
        gray_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        inv_gray = 255 - gray_img
        
        # Apply Gaussian blur
        blur = cv2.GaussianBlur(inv_gray, (21, 21), 0)
        
        # Divide the grayscale image by the blurred image
        pencil_sketch = cv2.divide(gray_img, 255 - blur, scale=256)
        
        # Convert back to PIL
        result = Image.fromarray(pencil_sketch)
        
        if spec.color and shade_factor > 0:
            # Create colored pencil sketch
            colored = cv2.stylization(cv_img, sigma_s=sigma_s, sigma_r=sigma_r)
            colored_pil = Image.fromarray(cv2.cvtColor(colored, cv2.COLOR_BGR2RGB))
            
            # Blend the colored image with the sketch based on shade_factor
            result = Image.blend(
                result.convert('RGB'), 
                colored_pil, 
                alpha=shade_factor
            )
        
        result = result.convert('RGBA')
        
        # Preserve original alpha channel if available
        if 'A' in image.getbands():
            result.putalpha(image.split()[3])
            
        return result
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.pencil_sketch.value


class ColorSplashFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        # Convert PIL to numpy array
        np_img = np.array(image.convert('RGB'))
        
        # Create grayscale version
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
        gray_rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        
        # If no color is specified, use a default color
        target_color = spec.color or (255, 0, 0)  # Default to red
        tolerance = spec.threshold or 30
        
        # Create mask for the target color
        mask = np.zeros_like(gray)
        
        if spec.color:
            # Create mask based on color similarity
            lower_bound = np.array([max(0, c - tolerance) for c in target_color])
            upper_bound = np.array([min(255, c + tolerance) for c in target_color])
            
            # Create boolean mask where color is within bounds
            color_mask = np.all((np_img >= lower_bound) & (np_img <= upper_bound), axis=2)
            mask[color_mask] = 255
            
            # Apply a slight blur to the mask for smoother transitions
            mask = cv2.GaussianBlur(mask, (5, 5), 0)
            
            # Normalize mask to range 0-1
            mask = mask / 255.0
            
            # Expand mask to 3 channels
            mask_rgb = np.stack([mask, mask, mask], axis=2)
            
            # Combine grayscale and color images based on mask
            result_np = gray_rgb * (1 - mask_rgb) + np_img * mask_rgb
            result = Image.fromarray(result_np.astype(np.uint8)).convert('RGBA')
        else:
            # Without a specific color, make the whole image grayscale
            result = Image.fromarray(gray_rgb).convert('RGBA')
        
        # Preserve original alpha channel if available
        if 'A' in image.getbands():
            result.putalpha(image.split()[3])
            
        return result
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.color_splash.value


class NoiseReductionFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        # Convert PIL to OpenCV
        cv_img = cv2.cvtColor(np.array(image.convert('RGB')), cv2.COLOR_RGB2BGR)
        
        # Parameters
        strength = spec.strength or 0.5
        preserve_details = spec.preserve_details if spec.preserve_details is not None else True
        
        # Choose appropriate denoising method based on parameters
        if preserve_details:
            # Non-local means denoising
            h = int(10 * strength)  # Filter strength 
            h_color = int(10 * strength)  # Color component filter strength
            template_size = 7  # Template patch size
            search_size = 21  # Search window size
            
            denoised = cv2.fastNlMeansDenoisingColored(
                cv_img, None, h, h_color, template_size, search_size
            )
        else:
            # Bilateral filter (preserves edges while removing noise)
            d = 9  # Diameter of pixel neighborhood
            sigma_color = int(75 * strength)  # Filter sigma in color space
            sigma_space = int(75 * strength)  # Filter sigma in coordinate space
            
            denoised = cv2.bilateralFilter(cv_img, d, sigma_color, sigma_space)
        
        # Convert back to PIL
        result = Image.fromarray(cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB)).convert('RGBA')
        
        # Preserve original alpha channel if available
        if 'A' in image.getbands():
            result.putalpha(image.split()[3])
            
        return result
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.noise_reduction.value


class GlitchFilter(FilterStrategy):
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        # Convert PIL to numpy array
        img_array = np.array(image)
        
        # Parameters
        intensity = spec.strength or 0.5
        seed = spec.threshold or random.randint(0, 100)
        random.seed(seed)
        
        # Make a copy to avoid modifying the original
        result_array = img_array.copy()
        
        # Get dimensions
        height, width = img_array.shape[:2]
        
        # Apply glitch effects based on intensity
        num_glitches = int(10 * intensity)
        
        for _ in range(num_glitches):
            # Choose random effect
            effect = random.randint(0, 3)
            
            if effect == 0:
                # Horizontal line shift
                y = random.randint(0, height - 1)
                h = random.randint(1, max(1, int(height * 0.1)))
                shift = random.randint(5, int(width * 0.2))
                
                for i in range(h):
                    if y + i < height:
                        row = result_array[y + i].copy()
                        result_array[y + i] = np.roll(row, shift, axis=0)
                        
            elif effect == 1:
                # Channel shift
                channel = random.randint(0, 2)
                y_start = random.randint(0, height - 1)
                y_end = min(height, y_start + random.randint(1, max(1, int(height * 0.2))))
                shift = random.randint(5, 20)
                
                for y in range(y_start, y_end):
                    result_array[y, :, channel] = np.roll(result_array[y, :, channel], shift)
                    
            elif effect == 2:
                # Noise
                y_start = random.randint(0, height - 1)
                y_end = min(height, y_start + random.randint(1, max(1, int(height * 0.1))))
                
                noise = np.random.randint(0, 255, (y_end - y_start, width, img_array.shape[2]))
                result_array[y_start:y_end] = noise
                
            else:
                # Swap regions
                h_size = max(1, int(height * 0.1))
                y1 = random.randint(0, height - h_size - 1)
                y2 = random.randint(0, height - h_size - 1)
                
                temp = result_array[y1:y1+h_size].copy()
                result_array[y1:y1+h_size] = result_array[y2:y2+h_size]
                result_array[y2:y2+h_size] = temp
        
        # Convert back to PIL
        result = Image.fromarray(result_array)
            
        return result
    
    @classmethod
    def filter_type(cls) -> str:
        return FilterType.glitch.value


# Register all filters with the factory
FilterFactory.register(OilPaintFilter)
FilterFactory.register(CartoonFilter)
FilterFactory.register(PencilSketchFilter)
FilterFactory.register(ColorSplashFilter)
FilterFactory.register(NoiseReductionFilter)
FilterFactory.register(GlitchFilter)

