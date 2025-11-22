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
from src.services.image_stegnography.core.service import ImageStegoService
from src.services.image_stegnography.models.stego_models import StegoTextHideRequest, StegoTextRevealRequest, StegoFileHideRequest, StegoOptions, BitPlaneVisualizerResult
from src.services.image_filters_and_effects.src.service import ImageEffectsService
from src.services.image_filters_and_effects.src.result import EffectsAPIResult
from src.services.image_filters_and_effects.models.effects_models import (EffectsInput, EffectsOptions,
    BackgroundAction, FilterSpec, OverlayItem, EraseShape)
from io import BytesIO
import io
from PIL import Image
import logging
import traceback
import os
import uuid
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Image Lab", version="1.0.0")

# Ensure output directories exist
os.makedirs("stego", exist_ok=True)
os.makedirs("stego_recovered", exist_ok=True)
os.makedirs("bit_planes", exist_ok=True)

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.mount("/files", StaticFiles(directory="stego"), name="stego")
app.mount("/recovered", StaticFiles(directory="stego_recovered"), name="recovered")
app.mount("/visualizations", StaticFiles(directory="bit_planes"), name="visualizations")


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

# --- Stats Tracking ---
class SystemStats:
    def __init__(self):
        self.encoded_count = 0
        self.decoded_count = 0
        self.total_bytes_processed = 0
        self.active_sessions = 1  # Mock for now

stats = SystemStats()

@app.get("/stats")
async def get_stats():
    return {
        "encoded_count": stats.encoded_count,
        "decoded_count": stats.decoded_count,
        "total_bytes_processed": stats.total_bytes_processed,
        "active_sessions": stats.active_sessions
    }

@app.post("/stego/capacity")
async def calculate_capacity(file: UploadFile = File(...)):
    """Calculates capacity for an image across all bit depths (1-8)."""
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        width, height = image.size
        pixels = width * height
        channels = len(image.getbands())
        
        capacity_data = []
        for bits in range(1, 9):
            total_bits = pixels * channels * bits
            bytes_capacity = total_bits // 8
            capacity_data.append({
                "bits": bits,
                "bytes": bytes_capacity,
                "pixels": pixels,
                "channels": channels
            })
            
        return {"filename": file.filename, "capacity": capacity_data}
    except Exception as e:
        logger.error(f"Error calculating capacity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Note: Convert and Effects endpoints temporarily omitted for brevity


@app.post("/stego/hide-text")
async def hide_text(
    file: UploadFile = File(...),
    text: str = Form(...),
    password: Optional[str] = Form(None),
    bits_per_channel: int = Form(1),
    lsb_depth: int = Form(1) # For backward compatibility
):
    try:
        # Handle parameter alias
        depth = bits_per_channel if bits_per_channel != 1 else lsb_depth
        
        logger.info(f"Received hide-text request: filename={file.filename}, text_len={len(text)}, bits={depth}, encrypted={bool(password)}")
        
        contents = await file.read()
        input_image = Image.open(io.BytesIO(contents))
        
        # Update stats
        stats.encoded_count += 1
        stats.total_bytes_processed += len(contents)
        
        # Create request object
        options = StegoOptions(
            password=password,
            bits_per_channel=depth
        )
        req = StegoTextHideRequest(
            text=text,
            options=options
        )
        
        result_image, result = stego_service.hide_text(input_image, req)
        
        output_filename = f"stego_{uuid.uuid4().hex}.png"
        output_path = os.path.join("stego", output_filename)
        result_image.save(output_path, format="PNG")
        
        return {
            "message": "Text hidden successfully",
            "output_path": f"files/{output_filename}",
            "used_capacity_bits": result.used_capacity_bits,
            "encrypted": bool(password)
        }
    except ValueError as e:
        logger.error(f"ValueError in hide-text: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in hide-text: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stego/reveal-text")
async def reveal_text(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None)
):
    try:
        logger.info(f"Received reveal-text request: filename={file.filename}, encrypted={bool(password)}")
        contents = await file.read()
        input_image = Image.open(io.BytesIO(contents))
        
        # Update stats
        stats.decoded_count += 1
        stats.total_bytes_processed += len(contents)
        
        # Create request object
        req = StegoTextRevealRequest(password=password)
        
        result = stego_service.reveal_text(input_image, req)
        
        return {"text": result.text}
    except ValueError as e:
        logger.warning(f"ValueError in reveal-text: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in reveal-text: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stego/hide-file")
async def hide_file(
    cover: UploadFile = File(...),
    secret: UploadFile = File(...),
    password: Optional[str] = Form(None),
    bits_per_channel: int = Form(1)
):
    try:
        logger.info(f"Received hide-file request: cover={cover.filename}, secret={secret.filename}, bits={bits_per_channel}")
        
        cover_bytes = await cover.read()
        secret_bytes = await secret.read()
        
        cover_image = Image.open(io.BytesIO(cover_bytes))
        
        # Update stats
        stats.encoded_count += 1
        stats.total_bytes_processed += len(cover_bytes) + len(secret_bytes)
        
        # Create request object
        options = StegoOptions(
            password=password,
            bits_per_channel=bits_per_channel
        )
        # Note: StegoFileHideRequest might not take file_bytes directly if service takes it separately
        # Service signature: hide_file(cover, req, filename, data)
        # So req just needs options
        req = StegoFileHideRequest(
            file_bytes=b"", # Placeholder if required, or maybe not needed if service takes data separately
            filename=secret.filename,
            options=options
        )
        
        result_image, result = stego_service.hide_file(
            cover_image,
            req,
            secret.filename,
            secret_bytes
        )
        
        output_filename = f"stego_file_{uuid.uuid4().hex}.png"
        output_path = os.path.join("stego", output_filename)
        result_image.save(output_path, format="PNG")
        
        return {
            "message": "File hidden successfully",
            "output_path": f"files/{output_filename}",
            "used_capacity_bits": result.used_capacity_bits,
            "encrypted": bool(password)
        }
    except Exception as e:
        logger.error(f"Error in hide-file: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stego/reveal-file")
async def reveal_file(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None)
):
    try:
        logger.info(f"Received reveal-file request: filename={file.filename}, encrypted={bool(password)}")
        contents = await file.read()
        input_image = Image.open(io.BytesIO(contents))
        
        # Update stats
        stats.decoded_count += 1
        stats.total_bytes_processed += len(contents)
        
        out_dir = Path("./stego_recovered")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        res = stego_service.reveal_file(input_image, password=password, output_dir=out_dir)
        
        return {
            "output_path": str(res.output_path),
            "filename": res.filename,
            "size_bytes": res.size_bytes
        }
    except Exception as e:
        logger.error(f"Error in reveal-file: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


from fastapi.responses import FileResponse

@app.post("/stego/visualize")
async def visualize_bit_planes(
    file: UploadFile = File(...),
    channel: str = Form("R"),
    bit_plane: Optional[int] = Form(None)
):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        request_id = uuid.uuid4().hex
        out_dir = Path("bit_planes") / request_id
        out_dir.mkdir(parents=True, exist_ok=True)
        
        if bit_plane is not None:
            res = stego_service.visualize_single_bit_plane(image, bit_plane, channel, out_dir)
            if res.output_images:
                return FileResponse(res.output_images[0])
            else:
                raise HTTPException(status_code=500, detail="No visualization generated")
        else:
            res = stego_service.visualize_bit_planes(image, channel, out_dir)
            
            # Convert paths to URLs
            image_urls = []
            for path in res.output_images:
                filename = path.name
                image_urls.append(f"visualizations/{request_id}/{filename}")
                
            return {
                "output_images": image_urls,
                "channel": res.channel,
                "bit_plane": res.bit_plane
            }
    except Exception as e:
        logger.error(f"Error in visualize: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


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

