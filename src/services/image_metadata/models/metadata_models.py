from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field


class MetadataInput(BaseModel):
    file_path: Optional[Path] = None
    image_bytes: Optional[bytes] = None
    url: Optional[str] = None


class GPSData(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    altitude_ref: Optional[int] = Field(default=None, description="0: above sea level, 1: below sea level")


class MetadataExtractResult(BaseModel):
    width: int
    height: int
    format: Optional[str] = None
    mode: Optional[str] = None

    exif: Dict[str, str] = Field(default_factory=dict)
    gps: GPSData = Field(default_factory=GPSData)
    datetime_original: Optional[str] = None
    datetime_digitized: Optional[str] = None
    datetime: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    software: Optional[str] = None


class MetadataUpdateRequest(BaseModel):
    # Common fields to update in EXIF
    datetime_original: Optional[str] = None
    datetime_digitized: Optional[str] = None
    datetime: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    software: Optional[str] = None
    artist: Optional[str] = None
    copyright: Optional[str] = None

    # GPS updates
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_altitude: Optional[float] = None
    gps_altitude_ref: Optional[int] = Field(default=None, description="0: above sea level, 1: below sea level")


class MetadataUpdateResult(BaseModel):
    output_path: Optional[Path]
    bytes_written: Optional[int] = None
    format: Optional[str] = None
    updated_fields: Dict[str, str] = Field(default_factory=dict)


class HashResult(BaseModel):
    ahash: str
    phash: str
    dhash: str
    whash: str


class IPTCData(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    byline: Optional[str] = None
    credit: Optional[str] = None
    source: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class MetadataDiffResult(BaseModel):
    left: MetadataExtractResult
    right: MetadataExtractResult
    diffs: Dict[str, dict]
    hash_hamming_distance: Optional[int] = None


class XMPWriteRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    creator: Optional[str] = None
    rights: Optional[str] = None
    subjects: list[str] = Field(default_factory=list)



