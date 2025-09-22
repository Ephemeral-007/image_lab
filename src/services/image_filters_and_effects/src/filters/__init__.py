from __future__ import annotations

# Import and register all filters
from .base import FilterStrategy
from .factory import FilterFactory
from .basic_filters import *
from .advanced_filters import *

# This ensures all filters are properly registered with the factory