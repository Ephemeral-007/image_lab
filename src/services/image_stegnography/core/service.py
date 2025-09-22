"""
Main service class for Image Steganography operations
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union

from PIL import Image

from ..models.stego_models import (
    BitPlaneVisualizerResult,
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
from .steganography import (
    calculate_capacity,
    embed_bits_into_image,
    extract_bits_from_image,
    build_payload,
    parse_payload,
    MAGIC,
)
from .encryption import decrypt_if_needed
from .compression import decompress_data
from .visualization import generate_all_bit_planes, generate_single_bit_plane
from ..utils.validation import validate_limits, validate_payload_fits
from ..utils.image_utils import calculate_pixel_count


class ImageStegoService:
    """
    Main service class for Image Steganography operations
    
    This service provides a high-level interface for all steganography operations
    including text/file hiding, revealing, capacity calculation, and bit plane visualization.
    """
    
    def capacity(
        self, 
        image: Image.Image, 
        bits_per_channel: int, 
        channels: Union[RGBChannel, List[RGBChannel]] = RGBChannel.ALL
    ) -> StegoCapacityResult:
        """
        Calculate steganography capacity for an image
        
        Args:
            image: Input image
            bits_per_channel: Number of bits per channel to use
            channels: Channels to use for steganography
            
        Returns:
            StegoCapacityResult with capacity information
        """
        total_bits, total_bytes, capacity_per_channel = calculate_capacity(
            image, bits_per_channel, channels
        )
        
        # Calculate header overhead
        header_overhead = len(MAGIC) + 1 + 4 + 4 + 1 + 1 + 2 + 2 + 2 + 1  # Base header size
        max_text_chars = max(0, (total_bytes - header_overhead))
        max_text_chars_pwd = max(0, (total_bytes - header_overhead - (16 + 12)))  # salt+nonce
        
        return StegoCapacityResult(
            capacity_bits=total_bits,
            capacity_bytes=total_bytes,
            max_text_chars_no_password=max_text_chars,
            max_text_chars_with_password=max_text_chars_pwd,
            capacity_per_channel=capacity_per_channel
        )

    def hide_text(
        self, 
        cover: Image.Image, 
        req: StegoTextHideRequest
    ) -> Tuple[Image.Image, StegoHideResult]:
        """
        Hide text in an image using steganography
        
        Args:
            cover: Cover image
            req: Text hiding request with options
            
        Returns:
            Tuple of (stego_image, result_metadata)
            
        Raises:
            ValueError: If limits are exceeded or capacity is insufficient
        """
        options = req.options
        channels = options.channels
        bits_per_channel = options.bits_per_channel
        
        # Calculate capacity
        total_bits, total_bytes, capacity_per_channel = calculate_capacity(
            cover, bits_per_channel, channels
        )
        
        # Build payload
        data = req.text.encode("utf-8")
        payload, is_compressed, compression_ratio = build_payload(
            payload_type=1, 
            data=data, 
            password=options.password, 
            filename=None,
            compress=options.compress,
            error_correction=options.error_correction.value,
            bits_per_channel=bits_per_channel,
            channels=channels
        )
        
        # Validate limits
        image_pixel_count = calculate_pixel_count(cover)
        validate_limits(options.limits, image_pixel_count, len(payload), total_bytes)
        validate_payload_fits(len(payload) * 8, total_bits)

        # Embed the payload
        stego_img = embed_bits_into_image(cover, payload, bits_per_channel, channels)
        
        # Get channel names for result
        channel_names = []
        if isinstance(channels, list):
            channel_names = [c.value for c in channels]
        else:
            channel_names = list(channels.value)
        
        # Prepare result
        result = StegoHideResult(
            output_path=Path(options.output_filename or "./stego_text.png"),
            used_capacity_bits=len(payload) * 8,
            payload_size_bytes=len(payload),
            overhead_bytes=len(payload) - len(data),
            encrypted=bool(options.password),
            encryption="AES-GCM" if options.password else None,
            kdf="Scrypt" if options.password else None,
            compression="zlib" if is_compressed else None,
            compression_ratio=compression_ratio if is_compressed else None,
            channels_used=channel_names,
            bits_per_channel=bits_per_channel
        )
        
        return stego_img, result

    def reveal_text(
        self, 
        stego_image: Image.Image, 
        req: StegoTextRevealRequest
    ) -> StegoRevealTextResult:
        """
        Reveal hidden text from a steganographic image
        
        Args:
            stego_image: Image with hidden text
            req: Text reveal request
            
        Returns:
            StegoRevealTextResult with revealed text and metadata
            
        Raises:
            ValueError: If payload is not text or decryption fails
        """
        # Start with 1 bpc and all channels to read header
        total_bits, total_bytes, _ = calculate_capacity(stego_image, 1, RGBChannel.ALL)
        
        # Read a reasonable prefix to parse header
        prefix_bits = min(total_bits, 8 * 4096)
        raw = extract_bits_from_image(stego_image, prefix_bits, 1, RGBChannel.ALL)
        
        # Parse header
        payload_type, is_compressed, bits_per_channel, salt, nonce, _, channels_str, enc = parse_payload(raw)
        
        if payload_type != 1:
            raise ValueError("Payload is not text")
        
        # Convert channels string to RGBChannel
        channels = []
        for c in channels_str:
            if c == 'R':
                channels.append(RGBChannel.RED)
            elif c == 'G':
                channels.append(RGBChannel.GREEN)
            elif c == 'B':
                channels.append(RGBChannel.BLUE)
        
        # If all channels are used, use the ALL enum
        if len(channels) == 3 and all(c in channels for c in [RGBChannel.RED, RGBChannel.GREEN, RGBChannel.BLUE]):
            channels = RGBChannel.ALL
        
        # Re-extract using the correct bits per channel and channels if needed
        if bits_per_channel > 1 or channels != RGBChannel.ALL:
            # Calculate needed header size
            total_len = len(MAGIC) + 1 + 4 + 4 + 1 + 1 + 2 + 2 + 2 + 1 + len(salt) + len(nonce) + len(enc) + len(channels_str)
            
            # Re-extract with correct parameters
            raw = extract_bits_from_image(stego_image, total_len * 8, bits_per_channel, channels)
            payload_type, is_compressed, bits_per_channel, salt, nonce, _, channels_str, enc = parse_payload(raw)
        
        # Attempt decrypt with password
        try:
            plain = decrypt_if_needed(enc, req.password, salt, nonce)
        except Exception as exc:
            raise ValueError("Invalid password or corrupted payload") from exc
        
        # Decompress if needed
        try:
            if is_compressed:
                plain = decompress_data(plain, is_compressed)
        except Exception as exc:
            raise ValueError("Failed to decompress payload") from exc
        
        # Build result
        channel_list = list(channels_str)
        return StegoRevealTextResult(
            text=plain.decode("utf-8", errors="replace"),
            was_compressed=is_compressed,
            channels_used=channel_list,
            bits_per_channel=bits_per_channel
        )

    def hide_file(
        self, 
        cover: Image.Image, 
        req: StegoFileHideRequest, 
        filename: str, 
        data: bytes
    ) -> Tuple[Image.Image, StegoHideResult]:
        """
        Hide a file in an image using steganography
        
        Args:
            cover: Cover image
            req: File hiding request with options
            filename: Name of the file to hide
            data: File data to hide
            
        Returns:
            Tuple of (stego_image, result_metadata)
            
        Raises:
            ValueError: If limits are exceeded or capacity is insufficient
        """
        options = req.options
        channels = options.channels
        bits_per_channel = options.bits_per_channel
        
        # Calculate capacity
        total_bits, total_bytes, capacity_per_channel = calculate_capacity(
            cover, bits_per_channel, channels
        )
        
        # Build payload
        payload, is_compressed, compression_ratio = build_payload(
            payload_type=2, 
            data=data, 
            password=options.password, 
            filename=filename,
            compress=options.compress,
            error_correction=options.error_correction.value,
            bits_per_channel=bits_per_channel,
            channels=channels
        )
        
        # Validate limits
        image_pixel_count = calculate_pixel_count(cover)
        validate_limits(options.limits, image_pixel_count, len(payload), total_bytes)
        validate_payload_fits(len(payload) * 8, total_bits)
        
        # Embed the payload
        stego_img = embed_bits_into_image(cover, payload, bits_per_channel, channels)
        
        # Get channel names for result
        channel_names = []
        if isinstance(channels, list):
            channel_names = [c.value for c in channels]
        else:
            channel_names = list(channels.value)
        
        # Prepare result
        result = StegoHideResult(
            output_path=Path(options.output_filename or "./stego_file.png"),
            used_capacity_bits=len(payload) * 8,
            payload_size_bytes=len(payload),
            overhead_bytes=len(payload) - len(data),
            encrypted=bool(options.password),
            encryption="AES-GCM" if options.password else None,
            kdf="Scrypt" if options.password else None,
            compression="zlib" if is_compressed else None,
            compression_ratio=compression_ratio if is_compressed else None,
            channels_used=channel_names,
            bits_per_channel=bits_per_channel
        )
        
        return stego_img, result

    def reveal_file(
        self, 
        stego_image: Image.Image, 
        password: str | None, 
        output_dir: Path
    ) -> StegoRevealFileResult:
        """
        Reveal hidden file from a steganographic image
        
        Args:
            stego_image: Image with hidden file
            password: Optional password for decryption
            output_dir: Directory to save revealed file
            
        Returns:
            StegoRevealFileResult with file information and metadata
            
        Raises:
            ValueError: If payload is not a file or decryption fails
        """
        # Start with 1 bpc and all channels to read header
        total_bits, total_bytes, _ = calculate_capacity(stego_image, 1, RGBChannel.ALL)
        
        # Read a reasonable prefix to parse header
        prefix_bits = min(total_bits, 8 * 8192)
        raw = extract_bits_from_image(stego_image, prefix_bits, 1, RGBChannel.ALL)
        
        # Parse header
        payload_type, is_compressed, bits_per_channel, salt, nonce, fname, channels_str, enc = parse_payload(raw)
        
        if payload_type != 2:
            raise ValueError("Payload is not file")
        
        # Convert channels string to RGBChannel
        channels = []
        for c in channels_str:
            if c == 'R':
                channels.append(RGBChannel.RED)
            elif c == 'G':
                channels.append(RGBChannel.GREEN)
            elif c == 'B':
                channels.append(RGBChannel.BLUE)
        
        # If all channels are used, use the ALL enum
        if len(channels) == 3 and all(c in channels for c in [RGBChannel.RED, RGBChannel.GREEN, RGBChannel.BLUE]):
            channels = RGBChannel.ALL
        
        # Re-extract using the correct bits per channel and channels if needed
        if bits_per_channel > 1 or channels != RGBChannel.ALL:
            # Calculate needed header size
            total_len = len(MAGIC) + 1 + 4 + 4 + 1 + 1 + 2 + 2 + 2 + 1 + len(salt) + len(nonce) + len(fname.encode("utf-8")) + len(channels_str) + len(enc)
            
            # Re-extract with correct parameters
            raw = extract_bits_from_image(stego_image, total_len * 8, bits_per_channel, channels)
            payload_type, is_compressed, bits_per_channel, salt, nonce, fname, channels_str, enc = parse_payload(raw)
        
        # Attempt decrypt with password
        try:
            plain = decrypt_if_needed(enc, password, salt, nonce)
        except Exception as exc:
            raise ValueError("Invalid password or corrupted payload") from exc
        
        # Decompress if needed
        try:
            if is_compressed:
                plain = decompress_data(plain, is_compressed)
        except Exception as exc:
            raise ValueError("Failed to decompress payload") from exc
        
        # Save the file
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / (fname or "recovered.bin")
        out_path.write_bytes(plain)
        
        # Build result
        channel_list = list(channels_str)
        return StegoRevealFileResult(
            output_path=out_path, 
            filename=out_path.name, 
            size_bytes=len(plain),
            was_compressed=is_compressed,
            channels_used=channel_list,
            bits_per_channel=bits_per_channel
        )

    def visualize_bit_planes(
        self,
        image: Image.Image,
        channel: str = "R",
        output_dir: Path = Path("./bit_planes")
    ) -> BitPlaneVisualizerResult:
        """
        Create visualizations for all bit planes of a specified channel
        
        Args:
            image: Input image
            channel: Color channel to visualize (R, G, or B)
            output_dir: Directory to save bit plane images
            
        Returns:
            BitPlaneVisualizerResult with output paths and metadata
        """
        return generate_all_bit_planes(image, channel, output_dir)
    
    def visualize_single_bit_plane(
        self,
        image: Image.Image,
        bit_plane: int,
        channel: str = "R",
        output_dir: Path = Path("./bit_planes")
    ) -> BitPlaneVisualizerResult:
        """
        Create a visualization for a specific bit plane of a specified channel
        
        Args:
            image: Input image
            bit_plane: The bit plane to visualize (0-7, where 0 is LSB)
            channel: Color channel to visualize (R, G, or B)
            output_dir: Directory to save bit plane image
            
        Returns:
            BitPlaneVisualizerResult with output path and metadata
        """
        return generate_single_bit_plane(image, bit_plane, channel, output_dir)
