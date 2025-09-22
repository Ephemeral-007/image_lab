"""
Error correction utilities for steganography operations
"""

from typing import Dict
from ..models.stego_models import ErrorCorrectionLevel


def add_error_correction(data: bytes, level: ErrorCorrectionLevel) -> bytes:
    """
    Add error correction based on level using simple repetition code
    
    Note: This is a basic implementation for demonstration.
    In production, more sophisticated error correction codes
    (Reed-Solomon, BCH, etc.) should be used.
    
    Args:
        data: Data to add error correction to
        level: Error correction level
        
    Returns:
        Data with error correction added
    """
    if level == ErrorCorrectionLevel.NONE:
        return data
    
    repetitions = {
        ErrorCorrectionLevel.LOW: 2,
        ErrorCorrectionLevel.MEDIUM: 3,
        ErrorCorrectionLevel.HIGH: 4
    }.get(level, 1)
    
    # Simple repetition code - repeat each byte N times
    result = bytearray()
    for b in data:
        for _ in range(repetitions):
            result.append(b)
    
    return bytes(result)


def correct_errors(data: bytes, level: ErrorCorrectionLevel) -> bytes:
    """
    Correct errors in data using the specified error correction level
    
    Args:
        data: Data with error correction
        level: Error correction level used
        
    Returns:
        Corrected data
        
    Raises:
        ValueError: If data is corrupted beyond correction capability
    """
    if level == ErrorCorrectionLevel.NONE:
        return data
    
    repetitions = {
        ErrorCorrectionLevel.LOW: 2,
        ErrorCorrectionLevel.MEDIUM: 3,
        ErrorCorrectionLevel.HIGH: 4
    }.get(level, 1)
    
    if len(data) % repetitions != 0:
        raise ValueError("Corrupted data for error correction")
    
    result = bytearray()
    for i in range(0, len(data), repetitions):
        chunk = data[i:i+repetitions]
        
        # Count occurrences of each value and use majority voting
        counts: Dict[int, int] = {}
        for b in chunk:
            counts[b] = counts.get(b, 0) + 1
        
        # Find the most common value
        max_count = 0
        max_byte = 0
        for b, count in counts.items():
            if count > max_count:
                max_count = count
                max_byte = b
        
        result.append(max_byte)
    
    return bytes(result)


def get_error_correction_overhead(level: ErrorCorrectionLevel) -> int:
    """
    Calculate the overhead added by error correction
    
    Args:
        level: Error correction level
        
    Returns:
        Multiplier for data size (e.g., 2 means data is 2x larger)
    """
    if level == ErrorCorrectionLevel.NONE:
        return 1
    
    repetitions = {
        ErrorCorrectionLevel.LOW: 2,
        ErrorCorrectionLevel.MEDIUM: 3,
        ErrorCorrectionLevel.HIGH: 4
    }.get(level, 1)
    
    return repetitions
