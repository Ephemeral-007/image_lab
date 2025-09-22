"""
API routes for the Image Steganography Service
"""

import os
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Union

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from ..models.stego_models import (
    BitPlaneVisualizerResult,
    ErrorCorrectionLevel,
    RGBChannel,
    StegoCapacityResult,
    StegoFileHideRequest,
    StegoHideResult,
    StegoOptions,
    StegoRevealFileResult,
    StegoRevealTextResult,
    StegoTextHideRequest,
    StegoTextRevealRequest,
)
from ..core.service import ImageStegoService
from .responses import StegoAPIResult

router = APIRouter(prefix="/stego", tags=["stego"])

# Ensure output directories exist
os.makedirs("./stego", exist_ok=True)
os.makedirs("./stego_recovered", exist_ok=True)
os.makedirs("./bit_planes", exist_ok=True)

# Service instance
stego_service = ImageStegoService()


def send_response(
    status_code: int, 
    message: str, 
    path: Optional[str] = None, 
    details: Optional[dict] = None
) -> JSONResponse:
    """
    Helper function to send consistent API responses
    
    Args:
        status_code: HTTP status code
        message: Response message
        path: Optional file path
        details: Optional additional details
        
    Returns:
        JSONResponse with consistent format
    """
    return JSONResponse(
        status_code=status_code,
        content=StegoAPIResult(
            success=status_code < 400,
            message=message,
            path=path,
            details=details
        ).dict()
    )


def parse_channels(channels: str) -> Union[RGBChannel, List[RGBChannel]]:
    """
    Parse channel string into RGBChannel enum(s)
    
    Args:
        channels: Channel string (e.g., "RGB", "RG", "B")
        
    Returns:
        RGBChannel enum or list of RGBChannel enums
    """
    channel_list = []
    if "R" in channels:
        channel_list.append(RGBChannel.RED)
    if "G" in channels:
        channel_list.append(RGBChannel.GREEN)
    if "B" in channels:
        channel_list.append(RGBChannel.BLUE)
    
    # If all channels, use the ALL enum
    if len(channel_list) == 3:
        return RGBChannel.ALL
    
    return channel_list


@router.post("/capacity", response_model=StegoCapacityResult)
async def check_capacity(
    file: UploadFile = File(...),
    bits_per_channel: int = Form(1),
    channels: str = Form("RGB"),
):
    """
    Check capacity of an image for steganography
    
    Args:
        file: The image file to check
        bits_per_channel: Number of bits per channel to use (1-8)
        channels: Channels to use (R, G, B, RG, RB, GB, RGB)
        
    Returns:
        StegoCapacityResult with capacity information
    """
    try:
        # Parse channels
        channel_value = parse_channels(channels)
        
        # Load image and calculate capacity
        img = Image.open(BytesIO(await file.read()))
        result = stego_service.capacity(img, bits_per_channel, channel_value)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/hide-text", response_model=StegoAPIResult)
async def hide_text(
    file: UploadFile = File(...),
    text: str = Form(...),
    password: Optional[str] = Form(None),
    bits_per_channel: int = Form(1),
    channels: str = Form("RGB"),
    compress: bool = Form(False),
    error_correction: str = Form("none"),
    output_filename: Optional[str] = Form(None),
):
    """
    Hide text in an image using steganography
    
    Args:
        file: Cover image
        text: Text to hide
        password: Optional password for encryption
        bits_per_channel: Number of LSB bits to use (1-8)
        channels: Channels to use (R, G, B, RG, RB, GB, RGB)
        compress: Whether to compress the text before embedding
        error_correction: Error correction level (none, low, medium, high)
        output_filename: Optional custom output filename
        
    Returns:
        StegoAPIResult with operation details
    """
    try:
        # Parse channels
        channel_value = parse_channels(channels)
        
        # Parse error correction
        ec_level = ErrorCorrectionLevel(error_correction)
        
        # Create options
        options = StegoOptions(
            bits_per_channel=bits_per_channel,
            password=password,
            channels=channel_value,
            compress=compress,
            error_correction=ec_level,
            output_filename=output_filename or "stego_text.png",
        )
        
        # Create request
        req = StegoTextHideRequest(text=text, options=options)
        
        # Process
        img = Image.open(BytesIO(await file.read()))
        stego_img, result = stego_service.hide_text(img, req)
        
        # Save result
        output_path = Path("./stego") / result.output_path.name
        stego_img.save(output_path, "PNG")
        
        # Return result
        return send_response(
            200, 
            f"Text hidden successfully using {result.bits_per_channel} bits per channel across {', '.join(result.channels_used)} channels",
            str(output_path),
            {
                "used_capacity_bits": result.used_capacity_bits,
                "payload_size_bytes": result.payload_size_bytes,
                "encrypted": result.encrypted,
                "compressed": result.compression is not None,
                "compression_ratio": result.compression_ratio,
                "channels": result.channels_used,
                "bits_per_channel": result.bits_per_channel
            }
        )
    except Exception as e:
        return send_response(400, str(e))


@router.post("/reveal-text", response_model=StegoAPIResult)
async def reveal_text(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
):
    """
    Reveal hidden text from a steganographic image
    
    Args:
        file: The steganographic image
        password: Optional password for decryption
        
    Returns:
        StegoAPIResult with revealed text and metadata
    """
    try:
        # Create request
        req = StegoTextRevealRequest(password=password)
        
        # Process
        img = Image.open(BytesIO(await file.read()))
        result = stego_service.reveal_text(img, req)
        
        # Return result
        return send_response(
            200, 
            f"Text revealed successfully from {result.bits_per_channel} bits per channel across {', '.join(result.channels_used)} channels",
            None,
            {
                "text": result.text,
                "was_compressed": result.was_compressed,
                "channels": result.channels_used,
                "bits_per_channel": result.bits_per_channel
            }
        )
    except ValueError as e:
        if "Invalid password" in str(e):
            return send_response(401, "Invalid password or corrupted payload")
        return send_response(400, str(e))
    except Exception as e:
        return send_response(400, str(e))


@router.post("/hide-file", response_model=StegoAPIResult)
async def hide_file(
    cover: UploadFile = File(...),
    secret: UploadFile = File(...),
    password: Optional[str] = Form(None),
    bits_per_channel: int = Form(1),
    channels: str = Form("RGB"),
    compress: bool = Form(False),
    error_correction: str = Form("none"),
    output_filename: Optional[str] = Form(None),
):
    """
    Hide a file in an image using steganography
    
    Args:
        cover: Cover image
        secret: File to hide
        password: Optional password for encryption
        bits_per_channel: Number of LSB bits to use (1-8)
        channels: Channels to use (R, G, B, RG, RB, GB, RGB)
        compress: Whether to compress the file before embedding
        error_correction: Error correction level (none, low, medium, high)
        output_filename: Optional custom output filename
        
    Returns:
        StegoAPIResult with operation details
    """
    try:
        # Parse channels
        channel_value = parse_channels(channels)
        
        # Parse error correction
        ec_level = ErrorCorrectionLevel(error_correction)
        
        # Create options
        options = StegoOptions(
            bits_per_channel=bits_per_channel,
            password=password,
            channels=channel_value,
            compress=compress,
            error_correction=ec_level,
            output_filename=output_filename or "stego_file.png",
        )
        
        # Create request
        req = StegoFileHideRequest(options=options)
        
        # Read files
        cover_img = Image.open(BytesIO(await cover.read()))
        secret_data = await secret.read()
        
        # Process
        stego_img, result = stego_service.hide_file(cover_img, req, secret.filename, secret_data)
        
        # Save result
        output_path = Path("./stego") / result.output_path.name
        stego_img.save(output_path, "PNG")
        
        # Return result
        return send_response(
            200, 
            f"File '{secret.filename}' hidden successfully using {result.bits_per_channel} bits per channel across {', '.join(result.channels_used)} channels",
            str(output_path),
            {
                "used_capacity_bits": result.used_capacity_bits,
                "payload_size_bytes": result.payload_size_bytes,
                "encrypted": result.encrypted,
                "compressed": result.compression is not None,
                "compression_ratio": result.compression_ratio,
                "channels": result.channels_used,
                "bits_per_channel": result.bits_per_channel
            }
        )
    except Exception as e:
        return send_response(400, str(e))


@router.post("/reveal-file", response_model=StegoAPIResult)
async def reveal_file(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
):
    """
    Reveal hidden file from a steganographic image
    
    Args:
        file: The steganographic image
        password: Optional password for decryption
        
    Returns:
        StegoAPIResult with file information and metadata
    """
    try:
        # Process
        img = Image.open(BytesIO(await file.read()))
        output_dir = Path("./stego_recovered")
        result = stego_service.reveal_file(img, password, output_dir)
        
        # Return result
        return send_response(
            200, 
            f"File '{result.filename}' revealed successfully from {result.bits_per_channel} bits per channel across {', '.join(result.channels_used)} channels",
            str(result.output_path),
            {
                "filename": result.filename,
                "size_bytes": result.size_bytes,
                "was_compressed": result.was_compressed,
                "channels": result.channels_used,
                "bits_per_channel": result.bits_per_channel
            }
        )
    except ValueError as e:
        if "Invalid password" in str(e):
            return send_response(401, "Invalid password or corrupted payload")
        return send_response(400, str(e))
    except Exception as e:
        return send_response(400, str(e))


@router.post("/visualize-bit-planes", response_model=StegoAPIResult)
async def visualize_bit_planes(
    file: UploadFile = File(...),
    channel: str = Form("R"),
):
    """
    Visualize all bit planes of an image for a specified channel
    
    Args:
        file: The image to visualize
        channel: Color channel to visualize (R, G, or B)
        
    Returns:
        StegoAPIResult with visualization details
    """
    try:
        # Validate channel
        if channel not in ["R", "G", "B"]:
            return send_response(400, "Channel must be R, G, or B")
        
        # Process
        img = Image.open(BytesIO(await file.read()))
        output_dir = Path("./bit_planes")
        result = stego_service.visualize_bit_planes(img, channel, output_dir)
        
        # Return result
        return send_response(
            200, 
            f"Generated {len(result.output_images)} bit plane visualizations for channel {channel}",
            None,
            {
                "output_images": [str(path) for path in result.output_images],
                "channel": result.channel,
            }
        )
    except Exception as e:
        return send_response(400, str(e))


@router.post("/visualize-single-bit-plane", response_model=StegoAPIResult)
async def visualize_single_bit_plane(
    file: UploadFile = File(...),
    bit_plane: int = Form(...),
    channel: str = Form("R"),
):
    """
    Visualize a specific bit plane of an image for a specified channel
    
    Args:
        file: The image to visualize
        bit_plane: The bit plane to visualize (0-7, where 0 is LSB)
        channel: Color channel to visualize (R, G, or B)
        
    Returns:
        StegoAPIResult with visualization details
    """
    try:
        # Validate inputs
        if bit_plane < 0 or bit_plane > 7:
            return send_response(400, "Bit plane must be between 0 and 7")
        if channel not in ["R", "G", "B"]:
            return send_response(400, "Channel must be R, G, or B")
        
        # Process
        img = Image.open(BytesIO(await file.read()))
        output_dir = Path("./bit_planes")
        result = stego_service.visualize_single_bit_plane(img, bit_plane, channel, output_dir)
        
        # Return result
        return send_response(
            200, 
            f"Generated bit plane {bit_plane} visualization for channel {channel}",
            str(result.output_images[0]),
            {
                "output_image": str(result.output_images[0]),
                "channel": result.channel,
                "bit_plane": result.bit_plane
            }
        )
    except Exception as e:
        return send_response(400, str(e))
