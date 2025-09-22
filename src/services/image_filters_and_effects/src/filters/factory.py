from __future__ import annotations

from typing import Dict, Type

from ...models.effects_models import FilterSpec, FilterType
from .base import FilterStrategy


class FilterFactory:
    """Factory for creating filter strategy objects.
    
    This implements the Factory pattern for creating filter strategy instances
    based on the filter type. The factory maintains a registry of filter strategies
    which can be dynamically registered at runtime.
    """
    
    _registry: Dict[str, Type[FilterStrategy]] = {}
    
    @classmethod
    def register(cls, filter_strategy: Type[FilterStrategy]) -> None:
        """Register a filter strategy class.
        
        Args:
            filter_strategy: The filter strategy class to register
        """
        filter_type = filter_strategy.filter_type()
        cls._registry[filter_type] = filter_strategy
    
    @classmethod
    def create(cls, spec: FilterSpec) -> FilterStrategy:
        """Create a filter strategy instance based on the filter specification.
        
        Args:
            spec: The filter specification
            
        Returns:
            An instance of the appropriate filter strategy
            
        Raises:
            ValueError: If the filter type is not registered
        """
        filter_type = spec.type.value
        if filter_type not in cls._registry:
            raise ValueError(f"Filter type '{filter_type}' is not registered")
        
        strategy_class = cls._registry[filter_type]
        return strategy_class()
    
    @classmethod
    def is_registered(cls, filter_type: FilterType) -> bool:
        """Check if a filter type is registered.
        
        Args:
            filter_type: The filter type to check
            
        Returns:
            True if registered, False otherwise
        """
        return filter_type.value in cls._registry
