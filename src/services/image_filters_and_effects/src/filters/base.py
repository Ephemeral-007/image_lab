from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from PIL import Image

from ...models.effects_models import FilterSpec


class FilterStrategy(ABC):
    """Abstract base class for filter strategies.
    
    This class implements the Strategy pattern for applying image filters.
    Each concrete filter implementation should inherit from this class
    and implement the apply method.
    """
    
    @abstractmethod
    def apply(self, image: Image.Image, spec: FilterSpec) -> Image.Image:
        """Apply the filter to the image.
        
        Args:
            image: The input image
            spec: The filter specification containing parameters
            
        Returns:
            Filtered image
        """
        pass
    
    @classmethod
    @abstractmethod
    def filter_type(cls) -> str:
        """Return the filter type string identifier.
        
        This should match the FilterType enum value.
        
        Returns:
            Filter type string
        """
        pass
