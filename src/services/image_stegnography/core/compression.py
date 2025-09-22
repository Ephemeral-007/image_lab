"""
Compression utilities for steganography operations
"""

import zlib
from typing import Tuple


def compress_data(data: bytes, level: int = 9) -> Tuple[bytes, bool]:
    """
    Compress data using zlib if it results in size reduction
    
    Args:
        data: Data to compress
        level: Compression level (1-9, 9 being highest)
        
    Returns:
        Tuple of (compressed_data, was_compressed)
    """
    if level < 1 or level > 9:
        level = 9  # Default to highest compression
    
    compressed = zlib.compress(data, level=level)
    
    # Only return compressed if it's actually smaller
    if len(compressed) < len(data):
        return compressed, True
    
    return data, False


def decompress_data(data: bytes, was_compressed: bool) -> bytes:
    """
    Decompress data if it was previously compressed
    
    Args:
        data: Data to potentially decompress
        was_compressed: Whether the data was compressed
        
    Returns:
        Decompressed or original data
        
    Raises:
        zlib.error: If decompression fails
    """
    if not was_compressed:
        return data
    
    try:
        return zlib.decompress(data)
    except zlib.error as e:
        raise ValueError(f"Failed to decompress payload: {e}")


def get_compression_ratio(original_size: int, compressed_size: int) -> float:
    """
    Calculate compression ratio
    
    Args:
        original_size: Size of original data
        compressed_size: Size of compressed data
        
    Returns:
        Compression ratio (original_size / compressed_size)
    """
    if compressed_size == 0:
        return 1.0
    return original_size / compressed_size
