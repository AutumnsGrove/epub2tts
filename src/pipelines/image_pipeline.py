"""
VLM Image Description Pipeline.

This module provides image description generation using local Vision-Language Models
for EPUB images with context-aware descriptions optimized for TTS.
"""

import logging
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import time
import pickle

from PIL import Image
import numpy as np

from ..utils.config import ImageConfig
from ..utils.logger import PerformanceLogger, ProgressLogger

logger = logging.getLogger(__name__)


@dataclass
class ImageDescription:
    """Container for image description with metadata."""
    image_path: str
    description: str
    context: str
    confidence: float
    processing_time: float
    model_used: str
    cache_hit: bool = False


@dataclass
class ImageProcessingResult:
    """Result of image processing operation."""
    success: bool
    descriptions: List[ImageDescription]
    total_images: int
    processed_images: int
    cache_hits: int
    total_processing_time: float
    error_message: Optional[str] = None


class ImageDescriptionCache:
    """Cache for image descriptions to avoid reprocessing."""

    def __init__(self, cache_dir: Path):
        """Initialize cache."""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_index_file = cache_dir / "cache_index.json"
        self.cache_index = self._load_cache_index()

    def _load_cache_index(self) -> Dict[str, Any]:
        """Load cache index from disk."""
        if self.cache_index_file.exists():
            try:
                with open(self.cache_index_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
        return {}

    def _save_cache_index(self) -> None:
        """Save cache index to disk."""
        try:
            with open(self.cache_index_file, 'w') as f:
                json.dump(self.cache_index, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache index: {e}")

    def _generate_cache_key(self, image_path: str, context: str) -> str:
        """Generate cache key from image and context."""
        # Use image file hash + context hash
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            image_hash = hashlib.md5(image_data).hexdigest()[:16]
        except Exception:
            # Fallback to path-based hash
            image_hash = hashlib.md5(image_path.encode()).hexdigest()[:16]

        context_hash = hashlib.md5(context.encode()).hexdigest()[:8]
        return f"{image_hash}_{context_hash}"

    def get(self, image_path: str, context: str = "") -> Optional[ImageDescription]:
        """Get cached description if available."""
        cache_key = self._generate_cache_key(image_path, context)

        if cache_key in self.cache_index:
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        description = pickle.load(f)
                    description.cache_hit = True
                    logger.debug(f"Cache hit for image: {Path(image_path).name}")
                    return description
                except Exception as e:
                    logger.warning(f"Failed to load cached description: {e}")
                    # Remove invalid cache entry
                    del self.cache_index[cache_key]
                    cache_file.unlink(missing_ok=True)

        return None

    def set(self, image_path: str, context: str, description: ImageDescription) -> None:
        """Cache image description."""
        cache_key = self._generate_cache_key(image_path, context)
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(description, f)

            self.cache_index[cache_key] = {
                'image_path': Path(image_path).name,  # Store only filename for privacy
                'timestamp': time.time(),
                'description_length': len(description.description)
            }

            self._save_cache_index()
            logger.debug(f"Cached description for image: {Path(image_path).name}")

        except Exception as e:
            logger.warning(f"Failed to cache description: {e}")

    def clear_old_entries(self, max_age_days: int = 30) -> None:
        """Clear cache entries older than specified days."""
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600

        old_keys = []
        for key, entry in self.cache_index.items():
            if current_time - entry.get('timestamp', 0) > max_age_seconds:
                old_keys.append(key)

        for key in old_keys:
            cache_file = self.cache_dir / f"{key}.pkl"
            cache_file.unlink(missing_ok=True)
            del self.cache_index[key]

        if old_keys:
            logger.info(f"Cleared {len(old_keys)} old cache entries")
            self._save_cache_index()


class BaseVLMModel:
    """Base class for Vision-Language Models."""

    def __init__(self, model_name: str, model_path: Optional[str] = None):
        """Initialize base VLM model."""
        self.model_name = model_name
        self.model_path = model_path
        self.is_loaded = False

    def load_model(self) -> bool:
        """Load the model. Override in subclasses."""
        raise NotImplementedError

    def generate_description(
        self,
        image: Image.Image,
        context: str = "",
        max_length: int = 100
    ) -> Tuple[str, float]:
        """
        Generate description for image.

        Args:
            image: PIL Image object
            context: Context text from surrounding content
            max_length: Maximum description length

        Returns:
            Tuple of (description, confidence_score)
        """
        raise NotImplementedError

    def unload_model(self) -> None:
        """Unload model to free memory."""
        pass


class MockVLMModel(BaseVLMModel):
    """Mock VLM model for development and testing."""

    def __init__(self, model_name: str = "mock-vlm"):
        """Initialize mock model."""
        super().__init__(model_name)
        logger.info("Initialized mock VLM model for development")

    def load_model(self) -> bool:
        """Load mock model (always succeeds)."""
        self.is_loaded = True
        return True

    def generate_description(
        self,
        image: Image.Image,
        context: str = "",
        max_length: int = 100
    ) -> Tuple[str, float]:
        """Generate mock description based on image properties."""
        # Create description based on image characteristics
        width, height = image.size
        mode = image.mode

        # Generate basic description
        if width > height:
            orientation = "landscape"
        elif height > width:
            orientation = "portrait"
        else:
            orientation = "square"

        # Try to detect dominant colors
        try:
            # Convert to RGB if necessary
            if mode != 'RGB':
                image = image.convert('RGB')

            # Get dominant color (simplified)
            colors = image.getcolors(maxcolors=256*256*256)
            if colors:
                dominant_color = max(colors, key=lambda x: x[0])[1]
                r, g, b = dominant_color
                if r > g and r > b:
                    color_desc = "reddish"
                elif g > r and g > b:
                    color_desc = "greenish"
                elif b > r and b > g:
                    color_desc = "bluish"
                else:
                    color_desc = "neutral-toned"
            else:
                color_desc = "colored"
        except Exception:
            color_desc = "toned"

        # Build description
        base_description = f"A {orientation} {color_desc} image"

        # Add context-based hints if available
        if context:
            context_lower = context.lower()
            if any(word in context_lower for word in ['person', 'people', 'man', 'woman']):
                base_description += " showing people"
            elif any(word in context_lower for word in ['building', 'house', 'city']):
                base_description += " of a building or structure"
            elif any(word in context_lower for word in ['nature', 'tree', 'forest', 'mountain']):
                base_description += " of a natural scene"
            elif any(word in context_lower for word in ['chart', 'graph', 'diagram']):
                base_description += " containing a chart or diagram"

        # Ensure description fits max length
        if len(base_description) > max_length:
            base_description = base_description[:max_length-3] + "..."

        # Mock confidence score
        confidence = 0.75 + (hash(str(image.size)) % 25) / 100

        return base_description, confidence


class LLaVAModel(BaseVLMModel):
    """LLaVA Vision-Language Model implementation."""

    def __init__(self, model_name: str = "llava-1.5-7b", model_path: Optional[str] = None):
        """Initialize LLaVA model."""
        super().__init__(model_name, model_path)
        self.model = None
        self.processor = None

    def load_model(self) -> bool:
        """Load LLaVA model."""
        try:
            # This would load the actual LLaVA model
            # For now, fall back to mock model
            logger.warning("LLaVA model not implemented, using mock model")
            return MockVLMModel().load_model()

        except Exception as e:
            logger.error(f"Failed to load LLaVA model: {e}")
            return False

    def generate_description(
        self,
        image: Image.Image,
        context: str = "",
        max_length: int = 100
    ) -> Tuple[str, float]:
        """Generate description using LLaVA."""
        # Placeholder - would use actual LLaVA inference
        mock_model = MockVLMModel()
        return mock_model.generate_description(image, context, max_length)


class ImageDescriptionPipeline:
    """
    Local VLM pipeline for image description generation.
    """

    def __init__(self, config: ImageConfig, cache_dir: Optional[Path] = None):
        """
        Initialize image description pipeline.

        Args:
            config: Image processing configuration
            cache_dir: Optional cache directory path
        """
        self.config = config
        self.cache_dir = cache_dir or Path(".vlm_cache")
        self.cache = ImageDescriptionCache(self.cache_dir)
        self.model: Optional[BaseVLMModel] = None

        logger.info(f"Initializing VLM pipeline with model: {config.model}")
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the VLM model."""
        try:
            model_name = self.config.model.lower()

            if "llava" in model_name:
                self.model = LLaVAModel(self.config.model, self.config.model_path)
            else:
                # Default to mock model for development
                logger.info("Using mock VLM model for development")
                self.model = MockVLMModel(self.config.model)

            if self.model.load_model():
                logger.info(f"VLM model loaded successfully: {self.config.model}")
            else:
                logger.error("Failed to load VLM model")
                self.model = None

        except Exception as e:
            logger.error(f"Error initializing VLM model: {e}")
            self.model = None

    def process_image(
        self,
        image_path: str,
        context: str = "",
        force_regenerate: bool = False
    ) -> ImageDescription:
        """
        Generate description for a single image.

        Args:
            image_path: Path to image file
            context: Surrounding text context
            force_regenerate: Force regeneration even if cached

        Returns:
            ImageDescription object
        """
        start_time = time.time()

        # Check cache first
        if not force_regenerate:
            cached_description = self.cache.get(image_path, context)
            if cached_description:
                return cached_description

        try:
            # Load and preprocess image
            image = Image.open(image_path)

            # Ensure image is in RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize if too large (for efficiency)
            max_size = 1024
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Generate description
            if self.model and self.model.is_loaded:
                with PerformanceLogger(f"VLM description generation"):
                    description_text, confidence = self.model.generate_description(
                        image,
                        context,
                        self.config.max_description_length
                    )
            else:
                description_text = "Image description unavailable (model not loaded)"
                confidence = 0.0

            # Post-process description for TTS
            description_text = self._post_process_description(description_text)

            processing_time = time.time() - start_time

            # Create description object
            description = ImageDescription(
                image_path=image_path,
                description=description_text,
                context=context[:200],  # Limit context storage
                confidence=confidence,
                processing_time=processing_time,
                model_used=self.model.model_name if self.model else "none"
            )

            # Cache the result
            self.cache.set(image_path, context, description)

            logger.debug(
                f"Generated description for {Path(image_path).name}: "
                f"{len(description_text)} chars, {processing_time:.2f}s"
            )

            return description

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return ImageDescription(
                image_path=image_path,
                description=f"Error processing image: {e}",
                context=context,
                confidence=0.0,
                processing_time=time.time() - start_time,
                model_used="error"
            )

    def batch_process_images(
        self,
        image_list: List[Dict[str, str]],
        parallel: bool = True
    ) -> ImageProcessingResult:
        """
        Process multiple images from EPUB.

        Args:
            image_list: List of image dictionaries with 'file_path', 'context', etc.
            parallel: Whether to use parallel processing

        Returns:
            ImageProcessingResult with processing summary
        """
        start_time = time.time()
        logger.info(f"Starting batch image processing: {len(image_list)} images")

        if not self.config.enabled:
            logger.info("Image description disabled in configuration")
            return ImageProcessingResult(
                success=True,
                descriptions=[],
                total_images=len(image_list),
                processed_images=0,
                cache_hits=0,
                total_processing_time=0.0
            )

        descriptions = []
        cache_hits = 0
        progress = ProgressLogger("Image processing", len(image_list))

        # Clean old cache entries periodically
        if len(image_list) > 10:  # Only for larger batches
            self.cache.clear_old_entries(max_age_days=7)

        if parallel and len(image_list) > 1:
            # Parallel processing using ThreadPoolExecutor
            from concurrent.futures import ThreadPoolExecutor, as_completed

            max_workers = min(4, len(image_list))  # Limit for memory usage
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_image = {}
                for image_info in image_list:
                    future = executor.submit(
                        self.process_image,
                        image_info['file_path'],
                        image_info.get('context', '')
                    )
                    future_to_image[future] = image_info

                # Collect results
                for future in as_completed(future_to_image):
                    try:
                        description = future.result()
                        descriptions.append(description)
                        if description.cache_hit:
                            cache_hits += 1
                        progress.update()
                    except Exception as e:
                        logger.error(f"Error in parallel image processing: {e}")
                        progress.update()

        else:
            # Sequential processing
            for image_info in image_list:
                description = self.process_image(
                    image_info['file_path'],
                    image_info.get('context', '')
                )
                descriptions.append(description)
                if description.cache_hit:
                    cache_hits += 1
                progress.update()

        progress.finish()

        total_processing_time = time.time() - start_time
        processed_images = len([d for d in descriptions if d.confidence > 0])

        logger.info(
            f"Batch image processing completed: "
            f"{processed_images}/{len(image_list)} processed, "
            f"{cache_hits} cache hits, {total_processing_time:.2f}s"
        )

        return ImageProcessingResult(
            success=True,
            descriptions=descriptions,
            total_images=len(image_list),
            processed_images=processed_images,
            cache_hits=cache_hits,
            total_processing_time=total_processing_time
        )

    def _post_process_description(self, description: str) -> str:
        """
        Post-process description for TTS optimization.

        Args:
            description: Raw description from VLM

        Returns:
            TTS-optimized description
        """
        # Remove common VLM artifacts
        processed = description.strip()

        # Ensure it ends with proper punctuation
        if processed and not processed.endswith(('.', '!', '?')):
            processed += '.'

        # Capitalize first letter
        if processed:
            processed = processed[0].upper() + processed[1:]

        # Replace problematic characters for TTS
        processed = processed.replace('"', '')
        processed = processed.replace("'", '')

        # Limit length
        if len(processed) > self.config.max_description_length:
            # Find last sentence within limit
            sentences = processed.split('.')
            result = ""
            for sentence in sentences:
                if len(result + sentence + '.') <= self.config.max_description_length:
                    result += sentence + '.'
                else:
                    break
            processed = result.rstrip('.')

        return processed

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        if self.model:
            return {
                'model_name': self.model.model_name,
                'model_path': self.model.model_path,
                'is_loaded': self.model.is_loaded,
                'cache_enabled': True,
                'cache_dir': str(self.cache_dir)
            }
        else:
            return {
                'model_name': 'none',
                'model_path': None,
                'is_loaded': False,
                'cache_enabled': True,
                'cache_dir': str(self.cache_dir)
            }

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.model:
            self.model.unload_model()
        logger.debug("VLM pipeline cleaned up")


def create_image_pipeline(config: ImageConfig) -> ImageDescriptionPipeline:
    """
    Factory function to create image description pipeline.

    Args:
        config: Image processing configuration

    Returns:
        Initialized image description pipeline
    """
    return ImageDescriptionPipeline(config)