"""
Core steganography algorithms for LSB embedding and extraction
"""

import struct
import numpy as np
from PIL import Image
from typing import Dict, List, Tuple, Union
from pathlib import Path

from ..models.stego_models import RGBChannel
from .encryption import encrypt_if_needed, decrypt_if_needed
from .compression import compress_data, decompress_data, get_compression_ratio
from .error_correction import add_error_correction, correct_errors
from ..utils.validation import validate_bits_per_channel, validate_channels


# Steganography header constants
MAGIC = b"STEG2"  # Updated magic for v2 with advanced features
VERSION = 2


def channel_to_indices(channel: Union[RGBChannel, List[RGBChannel]]) -> List[int]:
    """
    Convert channel specification to array indices (R=0, G=1, B=2)
    
    Args:
        channel: Channel or list of channels
        
    Returns:
        List of channel indices
    """
    channel_map = {
        RGBChannel.RED: [0],
        RGBChannel.GREEN: [1],
        RGBChannel.BLUE: [2],
        RGBChannel.ALL: [0, 1, 2]
    }
    
    if isinstance(channel, list):
        indices = []
        for ch in channel:
            indices.extend(channel_map.get(ch, []))
        return sorted(list(set(indices)))
    
    return channel_map.get(channel, [0, 1, 2])


def calculate_capacity(
    image: Image.Image, 
    bits_per_channel: int, 
    channels: Union[RGBChannel, List[RGBChannel]]
) -> Tuple[int, int, Dict[str, int]]:
    """
    Calculate steganography capacity considering bits per channel and channel selection
    
    Args:
        image: Input image
        bits_per_channel: Number of bits per channel
        channels: Channels to use
        
    Returns:
        Tuple of (total_bits, total_bytes, capacity_per_channel)
    """
    # Validate inputs
    validate_bits_per_channel(bits_per_channel)
    validate_channels(channels)
    
    # Ensure image is in RGB mode
    rgb = image.convert("RGB")
    w, h = rgb.size
    
    # Get indices of channels to use
    channel_indices = channel_to_indices(channels)
    num_channels = len(channel_indices)
    
    # Calculate capacity
    total_bits = w * h * num_channels * bits_per_channel
    
    # Calculate per-channel capacity
    channel_names = ['R', 'G', 'B']
    capacity_per_channel = {
        channel_names[idx]: w * h * bits_per_channel
        for idx in channel_indices
    }
    
    return total_bits, total_bits // 8, capacity_per_channel


def embed_bits_into_image(
    image: Image.Image, 
    payload: bytes, 
    bits_per_channel: int, 
    channels: Union[RGBChannel, List[RGBChannel]]
) -> Image.Image:
    """
    Embed payload bits into image using specified bits per channel and channels
    
    Args:
        image: Cover image
        payload: Data to embed
        bits_per_channel: Number of bits per channel
        channels: Channels to use
        
    Returns:
        Image with embedded data
    """
    # Validate inputs
    validate_bits_per_channel(bits_per_channel)
    validate_channels(channels)
    
    # Ensure image is in RGB mode
    rgb = image.convert("RGB")
    arr = np.array(rgb, dtype=np.uint8)
    w, h, _ = arr.shape
    
    # Determine which channels to use
    channel_indices = channel_to_indices(channels)
    
    # Convert payload to bits
    payload_bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    total_bits_needed = len(payload_bits)
    
    # Create a flat view for each channel
    channel_arrays = [arr[:, :, i].reshape(-1) for i in range(3)]
    selected_channels = [channel_arrays[i] for i in channel_indices]
    
    # Create bit masks
    mask = ((1 << bits_per_channel) - 1)
    clear_mask = 0xFF ^ mask
    
    # Distribute bits across channels
    bit_index = 0
    for pixel_index in range(w * h):
        if bit_index >= total_bits_needed:
            break
            
        for ch_idx, channel in enumerate(selected_channels):
            for bit_offset in range(bits_per_channel):
                if bit_index >= total_bits_needed:
                    break
                    
                # Clear bits and set with payload bit
                current = channel[pixel_index] & clear_mask
                bit_to_set = payload_bits[bit_index] << bit_offset
                channel[pixel_index] = current | bit_to_set
                bit_index += 1
    
    return Image.fromarray(arr, mode="RGB")


def extract_bits_from_image(
    image: Image.Image, 
    num_bits: int, 
    bits_per_channel: int, 
    channels: Union[RGBChannel, List[RGBChannel]]
) -> bytes:
    """
    Extract bits from image using specified bits per channel and channels
    
    Args:
        image: Image with embedded data
        num_bits: Number of bits to extract
        bits_per_channel: Number of bits per channel used
        channels: Channels used for embedding
        
    Returns:
        Extracted data as bytes
    """
    # Validate inputs
    validate_bits_per_channel(bits_per_channel)
    validate_channels(channels)
    
    # Ensure image is in RGB mode
    rgb = image.convert("RGB")
    arr = np.array(rgb, dtype=np.uint8)
    w, h, _ = arr.shape
    
    # Determine which channels to use
    channel_indices = channel_to_indices(channels)
    
    # Create a flat view for each channel
    channel_arrays = [arr[:, :, i].reshape(-1) for i in range(3)]
    selected_channels = [channel_arrays[i] for i in channel_indices]
    
    # Create bit masks for extraction
    mask = ((1 << bits_per_channel) - 1)
    
    # Extract bits
    bits_list = []
    bit_index = 0
    for pixel_index in range(w * h):
        for ch_idx, channel in enumerate(selected_channels):
            for bit_offset in range(bits_per_channel):
                if bit_index >= num_bits:
                    break
                
                # Extract the bit
                bit = (channel[pixel_index] >> bit_offset) & 0x01
                bits_list.append(bit)
                bit_index += 1
                
            if bit_index >= num_bits:
                break
                
        if bit_index >= num_bits:
            break
    
    # Convert extracted bits to bytes
    bit_array = np.array(bits_list, dtype=np.uint8)
    # Pad to multiple of 8
    rem = (-len(bit_array)) % 8
    if rem:
        bit_array = np.concatenate([bit_array, np.zeros(rem, dtype=np.uint8)])
    
    return np.packbits(bit_array).tobytes()


def build_payload(
    payload_type: int, 
    data: bytes, 
    password: str | None, 
    filename: str | None,
    compress: bool = False,
    error_correction_level: str = "none",
    bits_per_channel: int = 1,
    channels: Union[RGBChannel, List[RGBChannel]] = RGBChannel.ALL
) -> Tuple[bytes, bool, float]:
    """
    Build payload with optional compression and error correction
    
    Args:
        payload_type: Type of payload (1=text, 2=file)
        data: Raw data to embed
        password: Optional password for encryption
        filename: Optional filename for file payloads
        compress: Whether to compress data
        error_correction_level: Error correction level
        bits_per_channel: Bits per channel used
        channels: Channels used
        
    Returns:
        Tuple of (full_payload, is_compressed, compression_ratio)
    """
    # Compress if requested
    compressed_data, is_compressed = compress_data(data, level=9)
    compression_ratio = get_compression_ratio(len(data), len(compressed_data))
    
    # Add error correction if requested
    from ..models.stego_models import ErrorCorrectionLevel
    ec_level = ErrorCorrectionLevel(error_correction_level)
    data_with_ec = add_error_correction(compressed_data, ec_level)
    
    # Encrypt if password provided
    enc, salt, nonce = encrypt_if_needed(data_with_ec, password)
    
    # Convert channel to a string representation for header
    channels_str = ""
    if isinstance(channels, list):
        channels_str = "".join([c.value for c in channels])
    else:
        channels_str = channels.value
    channels_bytes = channels_str.encode("utf-8")
    
    # Convert filename to bytes
    fname_bytes = (filename or "").encode("utf-8")
    
    # Build header
    header = MAGIC + struct.pack(
        ">BIIBBHHHB",
        VERSION,
        payload_type,
        len(enc),
        int(is_compressed),
        bits_per_channel,
        len(salt),
        len(nonce),
        len(fname_bytes),
        len(channels_bytes),
    )
    
    # Build full payload
    full_payload = header + salt + nonce + fname_bytes + channels_bytes + enc
    
    return full_payload, is_compressed, compression_ratio


def parse_payload(raw: bytes) -> Tuple[int, bool, int, bytes, bytes, str, str, bytes]:
    """
    Parse payload header and extract components
    
    Args:
        raw: Raw payload data
        
    Returns:
        Tuple of (payload_type, is_compressed, bits_per_channel, salt, nonce, filename, channels_str, encrypted_data)
        
    Raises:
        ValueError: If header is invalid
    """
    if not raw.startswith(MAGIC):
        raise ValueError(f"Invalid stego header: expected {MAGIC!r}")
    
    off = len(MAGIC)
    version, payload_type, enc_len, is_compressed, bits_per_channel, salt_len, nonce_len, fname_len, channels_len = struct.unpack(
        ">BIIBBHHHB", raw[off : off + 1 + 4 + 4 + 1 + 1 + 2 + 2 + 2 + 1]
    )
    off += 1 + 4 + 4 + 1 + 1 + 2 + 2 + 2 + 1
    
    # Read components
    salt = raw[off : off + salt_len]
    off += salt_len
    
    nonce = raw[off : off + nonce_len]
    off += nonce_len
    
    fname = raw[off : off + fname_len].decode("utf-8", errors="ignore")
    off += fname_len
    
    channels_str = raw[off : off + channels_len].decode("utf-8", errors="ignore")
    off += channels_len
    
    enc = raw[off : off + enc_len]
    
    return payload_type, bool(is_compressed), bits_per_channel, salt, nonce, fname, channels_str, enc
