"""
API response models for the Image Steganography Service
"""

from pydantic import BaseModel
from typing import Any, Dict, Optional


class StegoAPIResult(BaseModel):
    """
    Standard API response model for all steganography endpoints
    """
    success: bool
    message: str
    path: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """
    Standard error response model
    """
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
