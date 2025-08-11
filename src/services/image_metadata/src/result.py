from __future__ import annotations

from pydantic import BaseModel


class ExtractAPIResult(BaseModel):
    width: int
    height: int
    format: str | None
    mode: str | None
    gps: dict
    datetime_original: str | None
    datetime_digitized: str | None
    datetime: str | None
    make: str | None
    model: str | None
    software: str | None

    class Config:
        arbitrary_types_allowed = True


class UpdateAPIResult(BaseModel):
    output_path: str | None
    bytes_written: int | None
    format: str | None
    updated_fields: dict[str, str]


class HashAPIResult(BaseModel):
    ahash: str
    phash: str
    dhash: str
    whash: str


class DiffAPIResult(BaseModel):
    diffs: dict
    hash_hamming_distance: int | None


