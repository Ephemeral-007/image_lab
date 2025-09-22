"""
Validation utilities for steganography operations
"""

from typing import Union
from .image_utils import calculate_pixel_count
from ..models.stego_models import StegoLimits, RGBChannel


def validate_bits_per_channel(bits_per_channel: int) -> None:
    """
    Validate bits per channel parameter
    
    Args:
        bits_per_channel: Number of bits to use per channel
        
    Raises:
        ValueError: If bits_per_channel is invalid
    """
    if not isinstance(bits_per_channel, int) or bits_per_channel < 1 or bits_per_channel > 8:
        raise ValueError("bits_per_channel must be an integer between 1 and 8")


def validate_channels(channels: Union[RGBChannel, list[RGBChannel]]) -> None:
    """
    Validate channel selection
    
    Args:
        channels: Channel or list of channels to validate
        
    Raises:
        ValueError: If channels are invalid
    """
    if isinstance(channels, list):
        if not channels:
            raise ValueError("At least one channel must be selected")
        for channel in channels:
            if not isinstance(channel, RGBChannel):
                raise ValueError(f"Invalid channel: {channel}")
    elif not isinstance(channels, RGBChannel):
        raise ValueError(f"Invalid channel type: {type(channels)}")


def validate_limits(limits: StegoLimits, image_pixel_count: int, payload_size: int, capacity_bytes: int) -> None:
    """
    Validate steganography limits
    
    Args:
        limits: StegoLimits object containing constraints
        image_pixel_count: Total pixels in cover image
        payload_size: Size of payload in bytes
        capacity_bytes: Available capacity in bytes
        
    Raises:
        ValueError: If any limits are exceeded
    """
    if limits.max_cover_pixels and image_pixel_count > limits.max_cover_pixels:
        raise ValueError(f"Cover image exceeds allowed pixel count: {image_pixel_count} > {limits.max_cover_pixels}")
    
    if limits.max_secret_bytes and payload_size > limits.max_secret_bytes:
        raise ValueError(f"Secret data exceeds allowed bytes: {payload_size} > {limits.max_secret_bytes}")
    
    if payload_size > capacity_bytes * limits.max_secret_ratio:
        raise ValueError(f"Secret data exceeds allowed ratio of capacity: {payload_size} > {capacity_bytes * limits.max_secret_ratio}")


def validate_payload_fits(payload_bits: int, available_bits: int) -> None:
    """
    Validate that payload fits in available capacity
    
    Args:
        payload_bits: Required bits for payload
        available_bits: Available bits in image
        
    Raises:
        ValueError: If payload doesn't fit
    """
    if payload_bits > available_bits:
        raise ValueError(f"Not enough capacity for payload: {payload_bits} > {available_bits}")
