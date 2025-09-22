"""
Bit plane visualization utilities for steganography analysis
"""

import numpy as np
from PIL import Image
from pathlib import Path
from typing import List
from ..models.stego_models import BitPlaneVisualizerResult


def extract_bit_plane(image: Image.Image, channel_idx: int, bit_plane: int) -> Image.Image:
    """
    Extract a specific bit plane from the image
    
    Args:
        image: Input PIL Image
        channel_idx: Channel index (0=R, 1=G, 2=B)
        bit_plane: Bit plane to extract (0-7, where 0 is LSB)
        
    Returns:
        Grayscale image showing the bit plane
    """
    if bit_plane < 0 or bit_plane > 7:
        raise ValueError("Bit plane must be between 0 and 7")
    
    # Ensure image is in RGB mode
    rgb = image.convert("RGB")
    arr = np.array(rgb)
    
    # Extract the specified channel
    channel = arr[:, :, channel_idx]
    
    # Extract the bit plane
    bit_mask = 1 << bit_plane
    bit_plane_data = ((channel & bit_mask) > 0).astype(np.uint8) * 255
    
    # Create a new image with the bit plane data
    return Image.fromarray(bit_plane_data, mode="L")


def generate_all_bit_planes(
    image: Image.Image, 
    channel: str, 
    output_dir: Path
) -> BitPlaneVisualizerResult:
    """
    Generate visualizations for all bit planes of a specified channel
    
    Args:
        image: Input PIL Image
        channel: Color channel to visualize (R, G, or B)
        output_dir: Directory to save bit plane images
        
    Returns:
        BitPlaneVisualizerResult with output paths and metadata
    """
    # Validate channel
    if channel not in ["R", "G", "B"]:
        raise ValueError("Channel must be R, G, or B")
    
    # Determine channel index
    channel_idx = {"R": 0, "G": 1, "B": 2}[channel]
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate bit plane images
    output_paths = []
    for bit in range(8):  # 8 bits per channel
        bit_plane_img = extract_bit_plane(image, channel_idx, bit)
        out_path = output_dir / f"bit_plane_{channel}_{bit}.png"
        bit_plane_img.save(out_path)
        output_paths.append(out_path)
    
    return BitPlaneVisualizerResult(
        output_images=output_paths,
        channel=channel,
        bit_plane=-1  # All bit planes
    )


def generate_single_bit_plane(
    image: Image.Image, 
    bit_plane: int, 
    channel: str, 
    output_dir: Path
) -> BitPlaneVisualizerResult:
    """
    Generate visualization for a specific bit plane of a specified channel
    
    Args:
        image: Input PIL Image
        bit_plane: The bit plane to visualize (0-7, where 0 is LSB)
        channel: Color channel to visualize (R, G, or B)
        output_dir: Directory to save bit plane image
        
    Returns:
        BitPlaneVisualizerResult with output path and metadata
    """
    # Validate inputs
    if bit_plane < 0 or bit_plane > 7:
        raise ValueError("Bit plane must be between 0 and 7")
    if channel not in ["R", "G", "B"]:
        raise ValueError("Channel must be R, G, or B")
    
    # Determine channel index
    channel_idx = {"R": 0, "G": 1, "B": 2}[channel]
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate bit plane image
    bit_plane_img = extract_bit_plane(image, channel_idx, bit_plane)
    out_path = output_dir / f"bit_plane_{channel}_{bit_plane}.png"
    bit_plane_img.save(out_path)
    
    return BitPlaneVisualizerResult(
        output_images=[out_path],
        channel=channel,
        bit_plane=bit_plane
    )


def create_bit_plane_comparison(
    image: Image.Image, 
    output_dir: Path
) -> List[Path]:
    """
    Create a comprehensive comparison of all bit planes for all channels
    
    Args:
        image: Input PIL Image
        output_dir: Directory to save comparison images
        
    Returns:
        List of output file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = []
    
    for channel in ["R", "G", "B"]:
        for bit in range(8):
            bit_plane_img = extract_bit_plane(image, {"R": 0, "G": 1, "B": 2}[channel], bit)
            out_path = output_dir / f"comparison_{channel}_bit_{bit}.png"
            bit_plane_img.save(out_path)
            output_paths.append(out_path)
    
    return output_paths
