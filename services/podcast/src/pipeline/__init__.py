"""
Pipeline module for podcast processing.

This module provides a step-based pipeline architecture for processing podcast episodes.
"""

from .config import PipelineConfig
from .service_container import ServiceContainer
from .episode_data import EpisodeData
from .processor import EpisodeProcessor

__all__ = [
    "PipelineConfig",
    "ServiceContainer",
    "EpisodeData",
    "EpisodeProcessor",
]




