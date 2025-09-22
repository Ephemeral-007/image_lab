from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.services.image_type_conversion.src.convertImageType import ConvertImageType
from src.services.image_type_conversion.models.conversion_models import AdvancedConversionOptions, BatchConversionRequest, ConversionInput, ConversionOptions, ResizeOptions, TargetImageFormat
from src.services.image_type_conversion.src.result import ConversionAPIResult
from src.services.image_metadata.src.service import ImageMetadataService
from src.services.image_metadata.models.metadata_models import MetadataInput, MetadataUpdateRequest
from src.services.image_metadata.src.result import DiffAPIResult, ExtractAPIResult, HashAPIResult, UpdateAPIResult
from src.services.image_resizer.src.service import ImageResizerService
from src.services.image_resizer.models.resizer_models import ResizerInput, ResizerOptions
from src.services.image_stegnography.src.service import ImageStegoService
from src.services.image_stegnography.models.stego_models import StegoTextHideRequest, StegoTextRevealRequest, StegoFileHideRequest
from src.services.image_filters_and_effects.src.service import ImageEffectsService
from src.services.image_filters_and_effects.src.result import EffectsAPIResult
from src.services.image_filters_and_effects.models.effects_models import (EffectsInput, EffectsOptions,
    BackgroundAction, FilterSpec, OverlayItem, EraseShape)
from io import BytesIO
from PIL import Image


app = FastAPI(title="Image Lab", version="1.0.0")


class ConvertQuery(BaseModel):
    to_format: TargetImageFormat
    background_color_rgba: Optional[tuple[int, int, int, int]] = (255, 255, 255, 255)
    quality: Optional[int] = 90
    keep_metadata: bool = True
    keep_animation: bool = False


converter = ConvertImageType()
metadata_service = ImageMetadataService()
resizer_service = ImageResizerService()
stego_service = ImageStegoService()
effects_service = ImageEffectsService()


@app.post("/convert", response_model=ConversionAPIResult)
async def convert_image(
    to_format: TargetImageFormat,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None,
):
    try:
        options = AdvancedConversionOptions(to_format=to_format)
        if file is not None:
            content = await file.read()
            conv_input = ConversionInput(image_bytes=content)
        elif url is not None:
            conv_input = ConversionInput(url=url)
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        output_dir = Path("./converted")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_filename = file.filename if file and file.filename else "output"
        output_path = output_dir / output_filename

        result = converter.convert(
            conv_input=conv_input,
            options=options,
            output_path=output_path,
        )

        return ConversionAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            output_format=result.output_format.value,
            width=result.width,
            height=result.height,
            num_frames=result.num_frames,
            was_animated=result.was_animated,
            metadata_preserved=result.metadata_preserved,
            bytes_written=result.bytes_written,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class AdvancedConvertQuery(BaseModel):
    to_format: TargetImageFormat
    resize: ResizeOptions | None = None
    compute_metrics: bool = False


@app.post("/convert/advanced", response_model=ConversionAPIResult)
async def convert_image_advanced(
    query: AdvancedConvertQuery,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None,
):
    try:
        options = AdvancedConversionOptions(to_format=query.to_format, resize=query.resize, compute_metrics=query.compute_metrics)
        if file is not None:
            content = await file.read()
            conv_input = ConversionInput(image_bytes=content)
            output_filename = file.filename or "output"
        elif url is not None:
            conv_input = ConversionInput(url=url)
            output_filename = "output"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        output_dir = Path("./converted")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename

        result = converter.convert(conv_input=conv_input, options=options, output_path=output_path)
        return ConversionAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            output_format=result.output_format.value,
            width=result.width,
            height=result.height,
            num_frames=result.num_frames,
            was_animated=result.was_animated,
            metadata_preserved=result.metadata_preserved,
            bytes_written=result.bytes_written,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class EffectsQuery(BaseModel):
    options: EffectsOptions


# Main effects endpoint for all effect options
@app.post("/effects", response_model=EffectsAPIResult)
async def apply_effects(query: EffectsQuery, file: UploadFile | None = File(default=None), url: str | None = None):
    try:
        if file is not None:
            content = await file.read()
            eff_input = EffectsInput(image_bytes=content)
            filename = file.filename or "effects.png"
        elif url is not None:
            eff_input = EffectsInput(url=url)
            filename = "effects.png"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        out_dir = Path("./effects")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / filename

        result = effects_service.apply(eff_input, query.options, output_path=output_path)
        return EffectsAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            width=result.width,
            height=result.height,
            bytes_written=result.bytes_written,
            extra=result.extra,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Background effects specific endpoint
class BackgroundQuery(BaseModel):
    background: BackgroundAction


@app.post("/effects/background", response_model=EffectsAPIResult)
async def apply_background_effect(query: BackgroundQuery, file: UploadFile | None = File(default=None), url: str | None = None):
    try:
        if file is not None:
            content = await file.read()
            eff_input = EffectsInput(image_bytes=content)
            filename = file.filename or "background_effect.png"
        elif url is not None:
            eff_input = EffectsInput(url=url)
            filename = "background_effect.png"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        out_dir = Path("./effects")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / filename

        options = EffectsOptions(background=query.background)
        result = effects_service.apply(eff_input, options, output_path=output_path)
        return EffectsAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            width=result.width,
            height=result.height,
            bytes_written=result.bytes_written,
            extra=result.extra,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Filters specific endpoint
class FiltersQuery(BaseModel):
    filters: list[FilterSpec]


@app.post("/effects/filters", response_model=EffectsAPIResult)
async def apply_filters(query: FiltersQuery, file: UploadFile | None = File(default=None), url: str | None = None):
    try:
        if file is not None:
            content = await file.read()
            eff_input = EffectsInput(image_bytes=content)
            filename = file.filename or "filtered.png"
        elif url is not None:
            eff_input = EffectsInput(url=url)
            filename = "filtered.png"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        out_dir = Path("./effects")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / filename

        options = EffectsOptions(filters=query.filters)
        result = effects_service.apply(eff_input, options, output_path=output_path)
        return EffectsAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            width=result.width,
            height=result.height,
            bytes_written=result.bytes_written,
            extra=result.extra,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Single filter application endpoint
class SingleFilterQuery(BaseModel):
    filter: FilterSpec


@app.post("/effects/filter", response_model=EffectsAPIResult)
async def apply_single_filter(query: SingleFilterQuery, file: UploadFile | None = File(default=None), url: str | None = None):
    try:
        if file is not None:
            content = await file.read()
            eff_input = EffectsInput(image_bytes=content)
            filename = file.filename or f"{query.filter.type}_filtered.png"
        elif url is not None:
            eff_input = EffectsInput(url=url)
            filename = f"{query.filter.type}_filtered.png"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        out_dir = Path("./effects")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / filename

        options = EffectsOptions(filters=[query.filter])
        result = effects_service.apply(eff_input, options, output_path=output_path)
        return EffectsAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            width=result.width,
            height=result.height,
            bytes_written=result.bytes_written,
            extra=result.extra,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Overlays specific endpoint
class OverlaysQuery(BaseModel):
    overlays: list[OverlayItem]


@app.post("/effects/overlays", response_model=EffectsAPIResult)
async def apply_overlays(query: OverlaysQuery, file: UploadFile | None = File(default=None), url: str | None = None):
    try:
        if file is not None:
            content = await file.read()
            eff_input = EffectsInput(image_bytes=content)
            filename = file.filename or "overlaid.png"
        elif url is not None:
            eff_input = EffectsInput(url=url)
            filename = "overlaid.png"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        out_dir = Path("./effects")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / filename

        options = EffectsOptions(overlays=query.overlays)
        result = effects_service.apply(eff_input, options, output_path=output_path)
        return EffectsAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            width=result.width,
            height=result.height,
            bytes_written=result.bytes_written,
            extra=result.extra,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Eraser specific endpoint
class EraseQuery(BaseModel):
    erase: list[EraseShape]


@app.post("/effects/erase", response_model=EffectsAPIResult)
async def apply_eraser(query: EraseQuery, file: UploadFile | None = File(default=None), url: str | None = None):
    try:
        if file is not None:
            content = await file.read()
            eff_input = EffectsInput(image_bytes=content)
            filename = file.filename or "erased.png"
        elif url is not None:
            eff_input = EffectsInput(url=url)
            filename = "erased.png"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        out_dir = Path("./effects")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / filename

        options = EffectsOptions(erase=query.erase)
        result = effects_service.apply(eff_input, options, output_path=output_path)
        return EffectsAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            width=result.width,
            height=result.height,
            bytes_written=result.bytes_written,
            extra=result.extra,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/effects/filters/available")
async def list_available_filters():
    """This endpoint lists all available filters"""
    from src.services.image_filters_and_effects.models.effects_models import FilterType
    basic_filters = [f for f in FilterType.__members__]
    
    try:
        # Check which advanced filters are available in the system
        from src.services.image_filters_and_effects.src.filters import FilterFactory
        available_filters = [filter_type for filter_type in FilterType.__members__ 
                          if FilterFactory.is_registered(FilterType(filter_type))]
        
        return {
            "all_filters": basic_filters,
            "available_filters": available_filters
        }
    except ImportError:
        # Fallback if FilterFactory is not accessible
        return {
            "all_filters": basic_filters
        }


@app.post("/stego/capacity")
async def stego_capacity(file: UploadFile = File(...), bits_per_channel: int = 1):
    try:
        img = Image.open(BytesIO(await file.read()))
        total_bits, total_bytes = img.width * img.height * 3 * bits_per_channel, (img.width * img.height * 3 * bits_per_channel) // 8
        # Reuse service for exact numbers and text max
        res = stego_service.capacity(img, bits_per_channel)
        return res.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/stego/hide-text")
async def stego_hide_text(file: UploadFile = File(...), text: str = Form(...), password: str | None = Form(default=None), bits_per_channel: int = Form(default=1)):
    try:
        cover = Image.open(BytesIO(await file.read()))
        req = StegoTextHideRequest(text=text, options={"password": password, "bits_per_channel": bits_per_channel})
        # Pydantic will parse dict into model
        req = StegoTextHideRequest.model_validate(req)
        stego_img, result = stego_service.hide_text(cover, req)
        out_dir = Path("./stego"); out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "stego_text.png"
        stego_img.save(out_path, format="PNG")
        return {
            "output_path": str(out_path),
            "used_capacity_bits": result.used_capacity_bits,
            "payload_size_bytes": result.payload_size_bytes,
            "encrypted": result.encrypted,
            "encryption": result.encryption,
            "kdf": result.kdf,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/stego/reveal-text")
async def stego_reveal_text(file: UploadFile = File(...), password: str | None = Form(default=None)):
    try:
        stego_img = Image.open(BytesIO(await file.read()))
        try:
            res = stego_service.reveal_text(stego_img, StegoTextRevealRequest(password=password))
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        return {"text": res.text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/stego/hide-file")
async def stego_hide_file(cover: UploadFile = File(...), secret: UploadFile = File(...), password: str | None = Form(default=None), bits_per_channel: int = Form(default=1)):
    try:
        cover_img = Image.open(BytesIO(await cover.read()))
        secret_bytes = await secret.read()
        req = StegoFileHideRequest(options={"password": password, "bits_per_channel": bits_per_channel})
        req = StegoFileHideRequest.model_validate(req)
        stego_img, result = stego_service.hide_file(cover_img, req, filename=secret.filename or "secret.bin", data=secret_bytes)
        out_dir = Path("./stego"); out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "stego_file.png"
        stego_img.save(out_path, format="PNG")
        return {"output_path": str(out_path), "used_capacity_bits": result.used_capacity_bits, "payload_size_bytes": result.payload_size_bytes}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/stego/reveal-file")
async def stego_reveal_file(file: UploadFile = File(...), password: str | None = Form(default=None)):
    try:
        stego_img = Image.open(BytesIO(await file.read()))
        out_dir = Path("./stego_recovered")
        res = stego_service.reveal_file(stego_img, password=password, output_dir=out_dir)
        return {"output_path": str(res.output_path), "filename": res.filename, "size_bytes": res.size_bytes}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class ResizeQuery(BaseModel):
    options: ResizerOptions


@app.post("/resize")
async def resize_image(query: ResizeQuery, file: UploadFile | None = File(default=None), url: str | None = None):
    try:
        if file is not None:
            content = await file.read()
            resizer_input = ResizerInput(image_bytes=content)
            filename = file.filename or "resized.jpg"
        elif url is not None:
            resizer_input = ResizerInput(url=url)
            filename = "resized.jpg"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        out_dir = Path("./resized")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / filename

        result = resizer_service.resize(resizer_input, query.options, output_path=output_path)
        return {
            "output_path": str(result.output_path) if result.output_path else None,
            "output_format": result.output_format.value,
            "width": result.width,
            "height": result.height,
            "bytes_written": result.bytes_written,
            "psnr": result.psnr,
            "ssim": result.ssim,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class BatchConvertQuery(BaseModel):
    targets: list[AdvancedConversionOptions]


@app.post("/convert/batch", response_model=list[ConversionAPIResult])
async def batch_convert(
    query: BatchConvertQuery,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None,
):
    try:
        if file is not None:
            content = await file.read()
            batch_request = BatchConversionRequest(image_bytes=content, targets=query.targets)
            output_filename = file.filename or "output"
        elif url is not None:
            batch_request = BatchConversionRequest(url=url, targets=query.targets)
            output_filename = "output"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        output_dir = Path("./converted/batch")
        results = converter.batch_convert(batch_request, output_dir=output_dir)
        api_results: list[ConversionAPIResult] = []
        for r in results:
            api_results.append(
                ConversionAPIResult(
                    output_path=str(r.output_path) if r.output_path else None,
                    output_format=r.output_format.value,
                    width=r.width,
                    height=r.height,
                    num_frames=r.num_frames,
                    was_animated=r.was_animated,
                    metadata_preserved=r.metadata_preserved,
                    bytes_written=r.bytes_written,
                )
            )
        return api_results
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/metadata/extract", response_model=ExtractAPIResult)
async def extract_metadata(file: UploadFile | None = File(default=None), url: str | None = None):
    try:
        if file is not None:
            content = await file.read()
            meta_input = MetadataInput(image_bytes=content)
        elif url is not None:
            meta_input = MetadataInput(url=url)
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        res = metadata_service.extract(meta_input)
        return ExtractAPIResult(
            width=res.width,
            height=res.height,
            format=res.format,
            mode=res.mode,
            gps=res.gps.model_dump(),
            datetime_original=res.datetime_original,
            datetime_digitized=res.datetime_digitized,
            datetime=res.datetime,
            make=res.make,
            model=res.model,
            software=res.software,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/metadata/update", response_model=UpdateAPIResult)
async def update_metadata(
    updates: MetadataUpdateRequest | None = None,
    updates_json: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    url: str | None = None,
):
    try:
        # Allow sending updates either as JSON body (no file) or as JSON string in form when uploading a file
        if updates is None and updates_json is not None:
            from pydantic import TypeAdapter
            updates = TypeAdapter(MetadataUpdateRequest).validate_json(updates_json)
        if updates is None:
            updates = MetadataUpdateRequest()

        if file is not None:
            content = await file.read()
            meta_input = MetadataInput(image_bytes=content)
            filename = file.filename or "updated.jpg"
        elif url is not None:
            meta_input = MetadataInput(url=url)
            filename = "updated.jpg"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        out_dir = Path("./metadata")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / filename

        result = metadata_service.update(meta_input, updates, output_path=output_path)
        return UpdateAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            bytes_written=result.bytes_written,
            format=result.format,
            updated_fields=result.updated_fields,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/metadata/strip", response_model=UpdateAPIResult)
async def strip_metadata(file: UploadFile | None = File(default=None), url: str | None = None):
    try:
        if file is not None:
            content = await file.read()
            meta_input = MetadataInput(image_bytes=content)
            filename = file.filename or "stripped.jpg"
        elif url is not None:
            meta_input = MetadataInput(url=url)
            filename = "stripped.jpg"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        out_dir = Path("./metadata")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / filename

        result = metadata_service.strip_all_metadata(meta_input, output_path=output_path)
        return UpdateAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            bytes_written=result.bytes_written,
            format=result.format,
            updated_fields=result.updated_fields,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/metadata/hashes", response_model=HashAPIResult)
async def metadata_hashes(file: UploadFile | None = File(default=None), url: str | None = None):
    try:
        if file is not None:
            content = await file.read()
            meta_input = MetadataInput(image_bytes=content)
        elif url is not None:
            meta_input = MetadataInput(url=url)
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        h = metadata_service.compute_hashes(meta_input)
        return HashAPIResult(ahash=h.ahash, phash=h.phash, dhash=h.dhash, whash=h.whash)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/metadata/normalize-orientation", response_model=UpdateAPIResult)
async def normalize_orientation(file: UploadFile | None = File(default=None), url: str | None = None):
    try:
        if file is not None:
            content = await file.read()
            meta_input = MetadataInput(image_bytes=content)
            filename = file.filename or "normalized.jpg"
        elif url is not None:
            meta_input = MetadataInput(url=url)
            filename = "normalized.jpg"
        else:
            raise HTTPException(status_code=400, detail="Provide either file or url")

        out_dir = Path("./metadata")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / filename

        result = metadata_service.normalize_orientation(meta_input, output_path=output_path)
        return UpdateAPIResult(
            output_path=str(result.output_path) if result.output_path else None,
            bytes_written=result.bytes_written,
            format=result.format,
            updated_fields=result.updated_fields,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/metadata/diff", response_model=DiffAPIResult)
async def metadata_diff(
    left_file: UploadFile | None = File(default=None),
    right_file: UploadFile | None = File(default=None),
    left_url: str | None = None,
    right_url: str | None = None,
):
    try:
        if left_file is not None:
            left_bytes = await left_file.read()
            left_input = MetadataInput(image_bytes=left_bytes)
        elif left_url is not None:
            left_input = MetadataInput(url=left_url)
        else:
            raise HTTPException(status_code=400, detail="Provide left_file or left_url")

        if right_file is not None:
            right_bytes = await right_file.read()
            right_input = MetadataInput(image_bytes=right_bytes)
        elif right_url is not None:
            right_input = MetadataInput(url=right_url)
        else:
            raise HTTPException(status_code=400, detail="Provide right_file or right_url")

        left_meta = metadata_service.extract(left_input)
        right_meta = metadata_service.extract(right_input)
        left_hash = metadata_service.compute_hashes(left_input)
        right_hash = metadata_service.compute_hashes(right_input)
        diff = metadata_service.diff(left_meta, right_meta, left_hash=left_hash, right_hash=right_hash)
        return DiffAPIResult(diffs=diff.diffs, hash_hamming_distance=diff.hash_hamming_distance)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

