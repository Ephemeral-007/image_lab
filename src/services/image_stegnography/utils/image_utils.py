"""
Image utility functions for steganography operations
"""

import httpx
from io import BytesIO
from typing import Optional
from PIL import Image


def load_image_from_input(file: Optional[BytesIO] = None, url: Optional[str] = None) -> Image.Image:
    """
    Load an image from either a file object or URL
    
    Args:
        file: BytesIO object containing image data
        url: URL to fetch image from
        
    Returns:
        PIL Image object
        
    Raises:
        ValueError: If neither file nor url is provided
    """
    if file is not None:
        return Image.open(file)
    if url is not None:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content))
    raise ValueError("Provide file or url")


def ensure_rgb_image(image: Image.Image) -> Image.Image:
    """
    Ensure image is in RGB mode for consistent processing
    
    Args:
        image: Input PIL Image
        
    Returns:
        Image converted to RGB mode
    """
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def get_image_dimensions(image: Image.Image) -> tuple[int, int]:
    """
    Get image dimensions
    
    Args:
        image: PIL Image object
        
    Returns:
        Tuple of (width, height)
    """
    return image.size


def calculate_pixel_count(image: Image.Image) -> int:
    """
    Calculate total number of pixels in image
    
    Args:
        image: PIL Image object
        
    Returns:
        Total pixel count
    """
    width, height = get_image_dimensions(image)
    return width * height
