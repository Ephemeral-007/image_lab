# Image Steganography API - Phase 4 Usage Guide

This guide demonstrates how to use the advanced LSB steganography features implemented in Phase 4.

## API Endpoints Overview

| Endpoint | Description |
|----------|-------------|
| `POST /stego/capacity` | Check image capacity for steganography with configurable bits and channels |
| `POST /stego/hide-text` | Hide text in image with advanced options |
| `POST /stego/reveal-text` | Reveal hidden text from image |
| `POST /stego/hide-file` | Hide any file in image with advanced options |
| `POST /stego/reveal-file` | Reveal hidden file from image |
| `POST /stego/visualize-bit-planes` | Generate visualizations for all bit planes of a channel |
| `POST /stego/visualize-single-bit-plane` | Generate visualization for a specific bit plane |

## New Phase 4 Features

### 1. Advanced Bit Plane Control

You can now choose how many LSB bits to use per channel (1-8), allowing greater capacity at the cost of image quality:

```bash
# Using 2 bits per channel for higher capacity
curl -X POST -F "file=@/path/to/cover.png" \
     -F "text=Secret message with higher capacity" \
     -F "bits_per_channel=2" \
     http://localhost:8000/stego/hide-text
```

### 2. RGB Channel Selection

Choose which color channels to use for hiding data:

```bash
# Hide data only in Red and Blue channels
curl -X POST -F "file=@/path/to/cover.png" \
     -F "text=This data is only in R and B channels" \
     -F "channels=RB" \
     http://localhost:8000/stego/hide-text
```

### 3. Compression Before Embedding

Optionally compress data before embedding to increase effective capacity:

```bash
# Compress text before hiding
curl -X POST -F "file=@/path/to/cover.png" \
     -F "text=This text will be compressed before embedding" \
     -F "compress=true" \
     http://localhost:8000/stego/hide-text
```

### 4. Error Correction

Add error correction to make your hidden data more resilient:

```bash
# Add medium level error correction
curl -X POST -F "file=@/path/to/cover.png" \
     -F "text=Error-protected message" \
     -F "error_correction=medium" \
     http://localhost:8000/stego/hide-text
```

### 5. Bit Plane Visualization

Visualize how steganography affects the bit planes of an image:

```bash
# Visualize all bit planes of the red channel
curl -X POST -F "file=@/path/to/stego_image.png" \
     -F "channel=R" \
     http://localhost:8000/stego/visualize-bit-planes

# Visualize just the least significant bit (LSB) of the blue channel
curl -X POST -F "file=@/path/to/stego_image.png" \
     -F "channel=B" \
     -F "bit_plane=0" \
     http://localhost:8000/stego/visualize-single-bit-plane
```

## Complete Examples

### Hide Text with All Advanced Features

```bash
curl -X POST -F "file=@/path/to/cover.png" \
     -F "text=This is a secret message with all advanced features" \
     -F "password=securepassword" \
     -F "bits_per_channel=2" \
     -F "channels=RG" \
     -F "compress=true" \
     -F "error_correction=low" \
     -F "output_filename=advanced_stego.png" \
     http://localhost:8000/stego/hide-text
```

### Hide File with All Advanced Features

```bash
curl -X POST -F "cover=@/path/to/cover.png" \
     -F "secret=@/path/to/secret.pdf" \
     -F "password=securepassword" \
     -F "bits_per_channel=3" \
     -F "channels=RGB" \
     -F "compress=true" \
     -F "error_correction=medium" \
     -F "output_filename=file_stego_advanced.png" \
     http://localhost:8000/stego/hide-file
```

### Check Capacity with Advanced Settings

```bash
curl -X POST -F "file=@/path/to/cover.png" \
     -F "bits_per_channel=4" \
     -F "channels=GB" \
     http://localhost:8000/stego/capacity
```

### Revealing Content

The reveal endpoints automatically detect the settings used to hide the data:

```bash
# Reveal text (no need to specify bits_per_channel or channels)
curl -X POST -F "file=@./stego/advanced_stego.png" \
     -F "password=securepassword" \
     http://localhost:8000/stego/reveal-text

# Reveal file
curl -X POST -F "file=@./stego/file_stego_advanced.png" \
     -F "password=securepassword" \
     http://localhost:8000/stego/reveal-file
```

## Capacity Considerations

The capacity of an image for steganography depends on:

1. **Image dimensions**: Larger images have more pixels to hide data
2. **Bits per channel**: Higher values store more data but reduce image quality
3. **Channel selection**: Using more channels increases capacity
4. **Compression**: Reduces the size of data before hiding

Formula: `capacity_bits = width × height × number_of_channels × bits_per_channel`

## Best Practices

1. For maximum stealth (visual imperceptibility), use:
   - 1 bit per channel
   - Limited to R and G channels (human eyes are less sensitive to blue)
   - Avoid compression if possible (potential artifacts)

2. For maximum capacity:
   - Use 2-3 bits per channel
   - Use all RGB channels
   - Enable compression
   - Consider lower error correction levels

3. For maximum security:
   - Use password protection
   - Use single bit plane (LSB)
   - Distribute across all channels
   - Keep payload small relative to capacity (< 25%)

4. For data integrity:
   - Use medium or high error correction
   - Use fewer bits per channel
   - Consider redundancy in vital information
