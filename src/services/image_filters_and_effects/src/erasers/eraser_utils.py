from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ...models.effects_models import EraseShape, EraseShapeType


def create_eraser_mask(image: Image.Image, shape: EraseShape) -> Image.Image:
    """
    Create an eraser mask based on the specified shape.
    
    Args:
        image: The source image
        shape: The eraser shape configuration
        
    Returns:
        A mask image (mode 'L') where white (255) represents areas to erase
    """
    mask = Image.new("L", image.size, 0)
    mdraw = ImageDraw.Draw(mask)
    
    if shape.type == EraseShapeType.rectangle and shape.width and shape.height:
        mdraw.rectangle([shape.x, shape.y, shape.x + shape.width, shape.y + shape.height], fill=255)
    
    elif shape.type == EraseShapeType.circle and shape.radius:
        mdraw.ellipse([
            shape.x - shape.radius, shape.y - shape.radius,
            shape.x + shape.radius, shape.y + shape.radius
        ], fill=255)
    
    elif shape.type == EraseShapeType.polygon and shape.polygon_points:
        if len(shape.polygon_points) >= 3:
            mdraw.polygon(shape.polygon_points, fill=255)
    
    elif shape.type == EraseShapeType.brush and shape.brush_points:
        # Draw brush stroke from points
        if len(shape.brush_points) > 1:
            brush_size = shape.brush_size or 20
            hardness = shape.brush_hardness or 0.5
            
            # Draw lines connecting points with round brush tip
            for i in range(len(shape.brush_points) - 1):
                p1 = shape.brush_points[i]
                p2 = shape.brush_points[i + 1]
                mdraw.line([p1, p2], fill=255, width=brush_size)
                mdraw.ellipse([
                    p1[0] - brush_size//2, p1[1] - brush_size//2,
                    p1[0] + brush_size//2, p1[1] + brush_size//2
                ], fill=255)
                
            # Draw final point
            last_point = shape.brush_points[-1]
            mdraw.ellipse([
                last_point[0] - brush_size//2, last_point[1] - brush_size//2,
                last_point[0] + brush_size//2, last_point[1] + brush_size//2
            ], fill=255)
            
            # Apply gaussian blur based on hardness (inverse relationship)
            # Hardness 1.0 = sharp edge, 0.0 = very soft edge
            blur_radius = brush_size * (1.0 - hardness) * 0.5
            if blur_radius > 0:
                mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    elif shape.type == EraseShapeType.smart and shape.color_mask:
        # Convert PIL to OpenCV
        cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGRA)
        
        # Extract target color
        target_color = shape.color_mask
        tolerance = shape.smart_tolerance or 30
        
        # Create a mask based on color similarity to the target color
        lower_bound = np.array([max(0, c - tolerance) for c in target_color] + [0])  # Add alpha
        upper_bound = np.array([min(255, c + tolerance) for c in target_color] + [255])  # Add alpha
        
        # Create the mask
        cv_mask = cv2.inRange(cv_img, lower_bound, upper_bound)
        
        # Optionally make it contiguous from a seed point
        if shape.smart_contiguous:
            # Create a mask for flood fill
            h, w = cv_mask.shape[:2]
            flood_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
            
            # Use the click point as seed
            seed_point = (shape.x, shape.y)
            
            # Flood fill from seed point
            cv2.floodFill(cv_mask, flood_mask, seed_point, 255, 0, 0, cv2.FLOODFILL_FIXED_RANGE)
            
            # Convert the result to a PIL mask
            mask = Image.fromarray(cv_mask)
        else:
            # Use the color mask directly
            mask = Image.fromarray(cv_mask)
    
    # Apply blur if requested
    if shape.blur and shape.type != EraseShapeType.brush:  # Brush already handles blur via hardness
        mask = mask.filter(ImageFilter.GaussianBlur(radius=shape.blur_radius))
        
    return mask


def apply_eraser(image: Image.Image, mask: Image.Image, mosaic: bool = False, mosaic_block: int = 16) -> Image.Image:
    """
    Apply eraser to image using mask.
    
    Args:
        image: Source image
        mask: Eraser mask (mode 'L')
        mosaic: If True, apply mosaic effect instead of transparency
        mosaic_block: Block size for mosaic effect
        
    Returns:
        Modified image
    """
    if mosaic:
        # Apply pixelation to the region
        region = Image.composite(image, Image.new("RGBA", image.size, (0, 0, 0, 0)), mask)
        
        # Apply pixelation to region
        block = max(2, mosaic_block)
        small = region.resize(
            (max(1, region.width // block), max(1, region.height // block)), 
            resample=Image.NEAREST
        )
        pixelated = small.resize(region.size, Image.NEAREST)
        
        return Image.composite(pixelated, image, mask)
    else:
        # Make the region transparent
        transparent = Image.new("RGBA", image.size, (0, 0, 0, 0))
        return Image.composite(transparent, image, mask)

