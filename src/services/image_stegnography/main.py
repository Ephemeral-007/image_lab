"""
Main entry point for the Image Steganography Service

This file provides the main router that can be included in the main FastAPI application.
"""

from .api.routes import router

# Export the router for easy inclusion in main app
__all__ = ["router"]
