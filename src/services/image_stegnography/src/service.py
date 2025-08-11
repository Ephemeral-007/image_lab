from __future__ import annotations

import os
import struct
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import httpx
import numpy as np
from PIL import Image
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from ..models.stego_models import (
    StegoCapacityResult,
    StegoFileHideRequest,
    StegoHideResult,
    StegoOptions,
    StegoRevealFileResult,
    StegoRevealTextResult,
    StegoTextHideRequest,
    StegoTextRevealRequest,
)


MAGIC = b"STEG1"  # header magic
VERSION = 1


def _load_image_from_input(file: Optional[BytesIO] = None, url: Optional[str] = None) -> Image.Image:
    if file is not None:
        return Image.open(file)
    if url is not None:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content))
    raise ValueError("Provide file or url")


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(password.encode("utf-8"))


def _encrypt_if_needed(data: bytes, password: Optional[str]) -> Tuple[bytes, bytes, bytes]:
    if not password:
        return data, b"", b""
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    enc = aesgcm.encrypt(nonce, data, None)
    return enc, salt, nonce


def _decrypt_if_needed(data: bytes, password: Optional[str], salt: bytes, nonce: bytes) -> bytes:
    if not password:
        return data
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, data, None)


def _capacity(image: Image.Image, bits_per_channel: int) -> Tuple[int, int]:
    # Only PNG (lossless) should be used for LSB
    rgb = image.convert("RGB")
    w, h = rgb.size
    total_bits = w * h * 3 * bits_per_channel
    return total_bits, total_bits // 8


def _embed_bits_into_image(image: Image.Image, payload: bytes, bits_per_channel: int) -> Image.Image:
    rgb = image.convert("RGB")
    arr = np.array(rgb, dtype=np.uint8)
    flat = arr.reshape(-1)

    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    num_bits = bits.shape[0]

    step = 8 // bits_per_channel
    # spread across channels evenly by writing low bits
    for i in range(0, num_bits):
        # index into flat array and choose which bit position
        byte_index = i // bits_per_channel
        bit_offset = i % bits_per_channel
        pixel_index = i
        if pixel_index >= flat.shape[0]:
            raise ValueError("Payload too large for the image capacity")
        # clear LSBs and set with payload bit for the selected offset
        mask = 0xFF ^ ((1 << bits_per_channel) - 1)
        current = flat[pixel_index] & mask
        current |= (bits[i] & 0x01) << bit_offset
        flat[pixel_index] = current

    out = flat.reshape(arr.shape)
    return Image.fromarray(out, mode="RGB")


def _extract_bits_from_image(image: Image.Image, num_bits: int, bits_per_channel: int) -> bytes:
    rgb = image.convert("RGB")
    arr = np.array(rgb, dtype=np.uint8)
    flat = arr.reshape(-1)

    mask = (1 << bits_per_channel) - 1
    bits_list = []
    for i in range(num_bits):
        pixel_index = i
        if pixel_index >= flat.shape[0]:
            raise ValueError("Requested bits exceed image capacity")
        lsb = flat[pixel_index] & mask
        bits_list.append(lsb & 0x01)

    bit_array = np.array(bits_list, dtype=np.uint8)
    # pad to multiple of 8
    rem = (-len(bit_array)) % 8
    if rem:
        bit_array = np.concatenate([bit_array, np.zeros(rem, dtype=np.uint8)])
    return np.packbits(bit_array, bitorder="big").tobytes()


def _build_payload(payload_type: int, data: bytes, password: Optional[str], filename: Optional[str]) -> bytes:
    enc, salt, nonce = _encrypt_if_needed(data, password)
    fname_bytes = (filename or "").encode("utf-8")
    header = MAGIC + struct.pack(
        ">BIIHHH",
        VERSION,
        payload_type,
        len(enc),
        len(salt),
        len(nonce),
        len(fname_bytes),
    )
    return header + salt + nonce + fname_bytes + enc


def _parse_payload(raw: bytes) -> Tuple[int, bytes, bytes, bytes, str, bytes]:
    if not raw.startswith(MAGIC):
        raise ValueError("Invalid stego header")
    off = len(MAGIC)
    version, payload_type, enc_len, salt_len, nonce_len, fname_len = struct.unpack(
        ">BIIHHH", raw[off : off + 1 + 4 + 4 + 2 + 2 + 2]
    )
    off += 1 + 4 + 4 + 2 + 2 + 2
    salt = raw[off : off + salt_len]
    off += salt_len
    nonce = raw[off : off + nonce_len]
    off += nonce_len
    fname = raw[off : off + fname_len].decode("utf-8", errors="ignore")
    off += fname_len
    enc = raw[off : off + enc_len]
    return payload_type, salt, nonce, enc, fname, raw[: off + enc_len]


class ImageStegoService:
    def capacity(self, image: Image.Image, bits_per_channel: int) -> StegoCapacityResult:
        total_bits, total_bytes = _capacity(image, bits_per_channel)
        # Rough estimates for max text characters considering minimal header
        header_overhead = len(MAGIC) + 1 + 4 + 2 + 2 + 2  # without optional parts
        max_text_chars = max(0, (total_bytes - header_overhead))
        max_text_chars_pwd = max(0, (total_bytes - header_overhead - (16 + 12)))  # salt+nonce
        return StegoCapacityResult(
            capacity_bits=total_bits,
            capacity_bytes=total_bytes,
            max_text_chars_no_password=max_text_chars,
            max_text_chars_with_password=max_text_chars_pwd,
        )

    def hide_text(self, cover: Image.Image, req: StegoTextHideRequest) -> Tuple[Image.Image, StegoHideResult]:
        total_bits, total_bytes = _capacity(cover, req.options.bits_per_channel)
        # Build payload
        data = req.text.encode("utf-8")
        payload = _build_payload(1, data, req.options.password, None)
        if req.options.limits.max_cover_pixels and (cover.width * cover.height) > req.options.limits.max_cover_pixels:
            raise ValueError("Cover image exceeds allowed pixel count")
        if req.options.limits.max_secret_bytes and len(payload) > req.options.limits.max_secret_bytes:
            raise ValueError("Secret data exceeds allowed bytes")
        if len(payload) > total_bytes * req.options.limits.max_secret_ratio:
            raise ValueError("Secret data exceeds allowed ratio of capacity")
        if len(payload) * 8 > total_bits:
            raise ValueError("Not enough capacity for payload")

        stego_img = _embed_bits_into_image(cover, payload, req.options.bits_per_channel)
        result = StegoHideResult(
            output_path=Path(req.options.output_filename or "./stego_text.png"),
            used_capacity_bits=len(payload) * 8,
            payload_size_bytes=len(payload),
            overhead_bytes=len(payload) - len(data),
            encrypted=bool(req.options.password),
            encryption="AES-GCM" if req.options.password else None,
            kdf="Scrypt" if req.options.password else None,
        )
        return stego_img, result

    def reveal_text(self, stego_image: Image.Image, req: StegoTextRevealRequest) -> StegoRevealTextResult:
        total_bits, total_bytes = _capacity(stego_image, 1)  # use 1 bpc for reading header robustly
        # Read a reasonable prefix to parse header
        prefix_bits = min(total_bits, 8 * 4096)
        raw = _extract_bits_from_image(stego_image, prefix_bits, 1)
        payload_type, salt, nonce, enc, _, _ = _parse_payload(raw)
        if payload_type != 1:
            raise ValueError("Payload is not text")
        # Attempt decrypt with password (may be empty)
        # If header was truncated in prefix, extract exact bits
        total_len = len(MAGIC) + 1 + 4 + 4 + 2 + 2 + 2 + len(salt) + len(nonce) + len(enc)
        if len(raw) < total_len:
            raw = _extract_bits_from_image(stego_image, total_len * 8, 1)
            payload_type, salt, nonce, enc, _, _ = _parse_payload(raw)
        try:
            plain = _decrypt_if_needed(enc, req.password, salt, nonce)
        except Exception as exc:
            raise ValueError("Invalid password or corrupted payload") from exc
        return StegoRevealTextResult(text=plain.decode("utf-8", errors="replace"))

    def hide_file(self, cover: Image.Image, req: StegoFileHideRequest, filename: str, data: bytes) -> Tuple[Image.Image, StegoHideResult]:
        total_bits, total_bytes = _capacity(cover, req.options.bits_per_channel)
        payload = _build_payload(2, data, req.options.password, filename)
        if req.options.limits.max_cover_pixels and (cover.width * cover.height) > req.options.limits.max_cover_pixels:
            raise ValueError("Cover image exceeds allowed pixel count")
        if req.options.limits.max_secret_bytes and len(payload) > req.options.limits.max_secret_bytes:
            raise ValueError("Secret data exceeds allowed bytes")
        if len(payload) > total_bytes * req.options.limits.max_secret_ratio:
            raise ValueError("Secret data exceeds allowed ratio of capacity")
        if len(payload) * 8 > total_bits:
            raise ValueError("Not enough capacity for payload")

        stego_img = _embed_bits_into_image(cover, payload, req.options.bits_per_channel)
        result = StegoHideResult(
            output_path=Path(req.options.output_filename or "./stego_file.png"),
            used_capacity_bits=len(payload) * 8,
            payload_size_bytes=len(payload),
            overhead_bytes=len(payload) - len(data),
        )
        return stego_img, result

    def reveal_file(self, stego_image: Image.Image, password: Optional[str], output_dir: Path) -> StegoRevealFileResult:
        total_bits, total_bytes = _capacity(stego_image, 1)
        prefix_bits = min(total_bits, 8 * 8192)
        raw = _extract_bits_from_image(stego_image, prefix_bits, 1)
        payload_type, salt, nonce, enc, fname, _ = _parse_payload(raw)
        if payload_type != 2:
            raise ValueError("Payload is not file")
        total_len = len(MAGIC) + 1 + 4 + 4 + 2 + 2 + 2 + len(salt) + len(nonce) + len(enc)
        if len(raw) < total_len:
            raw = _extract_bits_from_image(stego_image, total_len * 8, 1)
            payload_type, salt, nonce, enc, fname, _ = _parse_payload(raw)
        try:
            plain = _decrypt_if_needed(enc, password, salt, nonce)
        except Exception as exc:
            raise ValueError("Invalid password or corrupted payload") from exc
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / (fname or "recovered.bin")
        out_path.write_bytes(plain)
        return StegoRevealFileResult(output_path=out_path, filename=out_path.name, size_bytes=len(plain))


