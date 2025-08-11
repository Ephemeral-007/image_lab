from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple

import httpx
import piexif
from PIL import Image

from ..models.metadata_models import (
    GPSData,
    HashResult,
    IPTCData,
    MetadataDiffResult,
    MetadataExtractResult,
    MetadataInput,
    MetadataUpdateRequest,
    MetadataUpdateResult,
    XMPWriteRequest,
)
from .xmp_utils import extract_xmp_from_bytes
import imagehash
from PIL import ImageOps


def _dms_from_decimal(value: float) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
    deg = int(abs(value))
    minutes_float = (abs(value) - deg) * 60
    minutes = int(minutes_float)
    seconds = round((minutes_float - minutes) * 60 * 100)
    return (deg, 1), (minutes, 1), (int(seconds), 100)


def _decimal_from_dms(dms) -> float:
    d = dms[0][0] / dms[0][1]
    m = dms[1][0] / dms[1][1]
    s = dms[2][0] / dms[2][1]
    return d + (m / 60.0) + (s / 3600.0)


def _load_image_and_exif(meta_input: MetadataInput) -> tuple[Image.Image, Dict]:
    if meta_input.file_path is not None:
        image = Image.open(str(meta_input.file_path))
        exif_bytes = image.info.get("exif")
    elif meta_input.image_bytes is not None:
        image = Image.open(BytesIO(meta_input.image_bytes))
        exif_bytes = image.info.get("exif")
    elif meta_input.url is not None:
        with httpx.Client(timeout=30) as client:
            resp = client.get(meta_input.url)
            resp.raise_for_status()
            image = Image.open(BytesIO(resp.content))
            exif_bytes = image.info.get("exif")
    else:
        raise ValueError("Provide file_path, image_bytes, or url")

    exif_dict: Dict = {}
    if exif_bytes:
        try:
            exif_dict = piexif.load(exif_bytes)
        except Exception:
            try:
                exif_dict = piexif.load(image.info.get("exif", b""))
            except Exception:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    else:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    return image, exif_dict


class ImageMetadataService:
    def strip_all_metadata(self, meta_input: MetadataInput, output_path: Optional[Path] = None) -> MetadataUpdateResult:
        image, _ = _load_image_and_exif(meta_input)
        final_output_path: Optional[Path] = output_path or Path("./metadata") / "stripped.jpg"
        final_output_path.parent.mkdir(parents=True, exist_ok=True)

        with BytesIO() as buf:
            image.save(buf, format="JPEG")
            data = buf.getvalue()
        final_output_path.write_bytes(data)
        return MetadataUpdateResult(output_path=final_output_path, bytes_written=final_output_path.stat().st_size, format="JPEG", updated_fields={})

    def extract(self, meta_input: MetadataInput) -> MetadataExtractResult:
        image, exif = _load_image_and_exif(meta_input)
        width, height = image.size

        gps = GPSData()
        gps_ifd = exif.get("GPS", {}) or {}
        if gps_ifd:
            try:
                if piexif.GPSIFD.GPSLatitude in gps_ifd and piexif.GPSIFD.GPSLatitudeRef in gps_ifd:
                    lat = _decimal_from_dms(gps_ifd[piexif.GPSIFD.GPSLatitude])
                    lat_ref = gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef, b"N").decode(errors="ignore").upper()
                    gps.latitude = -lat if lat_ref == "S" else lat
                if piexif.GPSIFD.GPSLongitude in gps_ifd and piexif.GPSIFD.GPSLongitudeRef in gps_ifd:
                    lon = _decimal_from_dms(gps_ifd[piexif.GPSIFD.GPSLongitude])
                    lon_ref = gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef, b"E").decode(errors="ignore").upper()
                    gps.longitude = -lon if lon_ref == "W" else lon
                if piexif.GPSIFD.GPSAltitude in gps_ifd:
                    alt_n, alt_d = gps_ifd[piexif.GPSIFD.GPSAltitude]
                    gps.altitude = alt_n / alt_d if alt_d else None
                if piexif.GPSIFD.GPSAltitudeRef in gps_ifd:
                    gps.altitude_ref = int(gps_ifd[piexif.GPSIFD.GPSAltitudeRef])
            except Exception:
                pass

        exif_0th = exif.get("0th", {}) or {}
        exif_ifd = exif.get("Exif", {}) or {}

        def _get_str(ifd: Dict, tag: int) -> Optional[str]:
            val = ifd.get(tag)
            if val is None:
                return None
            if isinstance(val, bytes):
                return val.decode(errors="ignore").strip("\x00")
            return str(val)

        result = MetadataExtractResult(
            width=width,
            height=height,
            format=getattr(image, "format", None),
            mode=image.mode,
            exif={},
            gps=gps,
            datetime_original=_get_str(exif_ifd, piexif.ExifIFD.DateTimeOriginal),
            datetime_digitized=_get_str(exif_ifd, piexif.ExifIFD.DateTimeDigitized),
            datetime=_get_str(exif_0th, piexif.ImageIFD.DateTime),
            make=_get_str(exif_0th, piexif.ImageIFD.Make),
            model=_get_str(exif_0th, piexif.ImageIFD.Model),
            software=_get_str(exif_0th, piexif.ImageIFD.Software),
        )
        # Optional XMP extraction if library available and input is a path
        try:
            if meta_input.file_path is not None:
                xmp = extract_xmp_from_bytes(str(meta_input.file_path))
                if xmp:
                    # put a few common research-useful properties into extra exif map
                    result.exif.update(xmp)
        except Exception:
            pass
        return result

    def update(self, meta_input: MetadataInput, updates: MetadataUpdateRequest, output_path: Optional[Path] = None) -> MetadataUpdateResult:
        image, exif = _load_image_and_exif(meta_input)

        exif.setdefault("0th", {})
        exif.setdefault("Exif", {})
        exif.setdefault("GPS", {})

        def _set_str(ifd: Dict, tag: int, value: Optional[str]):
            if value is None:
                return
            ifd[tag] = value.encode("utf-8")

        updated: Dict[str, str] = {}

        _set_str(exif["Exif"], piexif.ExifIFD.DateTimeOriginal, updates.datetime_original)
        _set_str(exif["Exif"], piexif.ExifIFD.DateTimeDigitized, updates.datetime_digitized)
        _set_str(exif["0th"], piexif.ImageIFD.DateTime, updates.datetime)
        _set_str(exif["0th"], piexif.ImageIFD.Make, updates.make)
        _set_str(exif["0th"], piexif.ImageIFD.Model, updates.model)
        _set_str(exif["0th"], piexif.ImageIFD.Software, updates.software)
        _set_str(exif["0th"], piexif.ImageIFD.Artist, updates.artist)
        _set_str(exif["0th"], piexif.ImageIFD.Copyright, updates.copyright)

        if any(
            v is not None
            for v in (
                updates.gps_latitude,
                updates.gps_longitude,
                updates.gps_altitude,
                updates.gps_altitude_ref,
            )
        ):
            gps = exif["GPS"]
            if updates.gps_latitude is not None:
                gps[piexif.GPSIFD.GPSLatitude] = _dms_from_decimal(abs(updates.gps_latitude))
                gps[piexif.GPSIFD.GPSLatitudeRef] = (b"S" if updates.gps_latitude < 0 else b"N")
                updated["gps_latitude"] = str(updates.gps_latitude)
            if updates.gps_longitude is not None:
                gps[piexif.GPSIFD.GPSLongitude] = _dms_from_decimal(abs(updates.gps_longitude))
                gps[piexif.GPSIFD.GPSLongitudeRef] = (b"W" if updates.gps_longitude < 0 else b"E")
                updated["gps_longitude"] = str(updates.gps_longitude)
            if updates.gps_altitude is not None:
                gps[piexif.GPSIFD.GPSAltitude] = (int(updates.gps_altitude * 100), 100)
                updated["gps_altitude"] = str(updates.gps_altitude)
            if updates.gps_altitude_ref is not None:
                gps[piexif.GPSIFD.GPSAltitudeRef] = int(updates.gps_altitude_ref)
                updated["gps_altitude_ref"] = str(updates.gps_altitude_ref)

        exif_bytes = piexif.dump(exif)

        # Ensure saving to JPEG or PNG (PNG won't preserve EXIF in Pillow). Prefer JPEG/TIFF/WebP.
        final_output_path: Optional[Path] = output_path
        if final_output_path is None:
            final_output_path = Path("./metadata") / "updated.jpg"
        final_output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to JPEG if original format cannot embed EXIF easily
        save_format = (image.format or "JPEG").upper()
        if save_format not in {"JPEG", "JPG", "TIFF", "WEBP"}:  # PNG doesn't support EXIF reliably
            save_format = "JPEG"
            final_output_path = final_output_path.with_suffix(".jpg")

        with BytesIO() as buf:
            image.save(buf, format=save_format, exif=exif_bytes)
            data = buf.getvalue()

        final_output_path.write_bytes(data)

        return MetadataUpdateResult(
            output_path=final_output_path,
            bytes_written=final_output_path.stat().st_size,
            format=save_format,
            updated_fields=updated,
        )

    def compute_hashes(self, meta_input: MetadataInput) -> HashResult:
        image, _ = _load_image_and_exif(meta_input)
        gray = ImageOps.exif_transpose(image).convert("L")
        return HashResult(
            ahash=str(imagehash.average_hash(gray)),
            phash=str(imagehash.phash(gray)),
            dhash=str(imagehash.dhash(gray)),
            whash=str(imagehash.whash(gray)),
        )

    def normalize_orientation(self, meta_input: MetadataInput, output_path: Optional[Path] = None) -> MetadataUpdateResult:
        image, exif = _load_image_and_exif(meta_input)
        fixed = ImageOps.exif_transpose(image)
        final_output_path: Optional[Path] = output_path or Path("./metadata") / "normalized.jpg"
        final_output_path.parent.mkdir(parents=True, exist_ok=True)

        exif_bytes = piexif.dump(exif)
        with BytesIO() as buf:
            fixed.save(buf, format=(image.format or "JPEG"), exif=exif_bytes)
            data = buf.getvalue()
        final_output_path.write_bytes(data)
        return MetadataUpdateResult(output_path=final_output_path, bytes_written=final_output_path.stat().st_size, format=image.format, updated_fields={})

    def diff(self, left: MetadataExtractResult, right: MetadataExtractResult, left_hash: HashResult | None = None, right_hash: HashResult | None = None) -> MetadataDiffResult:
        diffs: Dict[str, dict] = {}
        fields = [
            "width",
            "height",
            "format",
            "mode",
            "datetime_original",
            "datetime_digitized",
            "datetime",
            "make",
            "model",
            "software",
        ]
        for f in fields:
            lv = getattr(left, f)
            rv = getattr(right, f)
            if lv != rv:
                diffs[f] = {"left": lv, "right": rv}

        # GPS compare
        if (left.gps.latitude != right.gps.latitude) or (left.gps.longitude != right.gps.longitude) or (left.gps.altitude != right.gps.altitude) or (left.gps.altitude_ref != right.gps.altitude_ref):
            diffs["gps"] = {"left": left.gps.model_dump(), "right": right.gps.model_dump()}

        # Hash distance if provided
        hamming = None
        if left_hash and right_hash:
            try:
                hamming = imagehash.hex_to_hash(left_hash.phash) - imagehash.hex_to_hash(right_hash.phash)
            except Exception:
                hamming = None

        return MetadataDiffResult(left=left, right=right, diffs=diffs, hash_hamming_distance=hamming)

    def write_xmp_sidecar(self, meta_input: MetadataInput, xmp: XMPWriteRequest, output_path: Optional[Path] = None) -> Path:
        # Sidecar XMP (minimal implementation without libxmp dependency)
        # Writes a .xmp file next to the desired output_path (or ./metadata/sidecar.xmp)
        from xml.sax.saxutils import escape

        final_output_path = output_path or (Path("./metadata") / "sidecar.xmp")
        final_output_path.parent.mkdir(parents=True, exist_ok=True)

        subjects_xml = "".join([f"<rdf:li>{escape(s)}</rdf:li>" for s in xmp.subjects])
        xml = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<x:xmpmeta xmlns:x=\"adobe:ns:meta/\">
  <rdf:RDF xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\" xmlns:dc=\"http://purl.org/dc/elements/1.1/\">
    <rdf:Description rdf:about=\"\">
      {f'<dc:title><rdf:Alt><rdf:li xml:lang=\'x-default\'>{escape(xmp.title or "")}</rdf:li></rdf:Alt></dc:title>'}
      {f'<dc:description><rdf:Alt><rdf:li xml:lang=\'x-default\'>{escape(xmp.description or "")}</rdf:li></rdf:Alt></dc:description>'}
      {f'<dc:creator><rdf:Seq><rdf:li>{escape(xmp.creator or "")}</rdf:li></rdf:Seq></dc:creator>'}
      {f'<dc:rights><rdf:Alt><rdf:li xml:lang=\'x-default\'>{escape(xmp.rights or "")}</rdf:li></rdf:Alt></dc:rights>'}
      {f'<dc:subject><rdf:Bag>{subjects_xml}</rdf:Bag></dc:subject>'}
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
"""
        final_output_path.write_text(xml, encoding="utf-8")
        return final_output_path


