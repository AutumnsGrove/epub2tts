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

from utils.config import ImageConfig
from utils.logger import PerformanceLogger, ProgressLogger
from ui.progress_tracker import (
    ProgressTracker, PipelineType, EventType,
    create_start_event, create_progress_event, create_complete_event, create_error_event
)

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


class GemmaVLMModel(BaseVLMModel):
    """Gemma-3n-e4b Vision-Language Model via LM Studio API."""

    def __init__(self, model_name: str = "gemma-3n-e4b", api_url: str = "http://127.0.0.1:1234"):
        """Initialize Gemma VLM model."""
        super().__init__(model_name)
        self.api_url = api_url.rstrip('/')
        self.api_endpoint = f"{self.api_url}/v1/chat/completions"
        self.session = None

    def load_model(self) -> bool:
        """Load/test Gemma model connection with auto-start capability."""
        try:
            import requests
            self.session = requests.Session()

            # Test connection to LM Studio
            test_response = self.session.get(f"{self.api_url}/v1/models", timeout=10)
            if test_response.status_code == 200:
                models = test_response.json()
                available_models = [m.get('id', 'unknown') for m in models.get('data', [])]
                logger.info(f"Connected to LM Studio. Available models: {available_models}")

                # Check if our model is loaded
                if self.model_name in available_models:
                    logger.info(f"Model {self.model_name} is already loaded")
                    self.is_loaded = True
                    return True
                else:
                    logger.info(f"Model {self.model_name} not loaded, attempting to load...")
                    return self._load_model_in_lm_studio()
            else:
                logger.error(f"LM Studio connection failed: {test_response.status_code}")
                logger.info("Attempting to start LM Studio...")
                return self._start_lm_studio_and_load_model()

        except Exception as e:
            logger.error(f"Failed to connect to LM Studio: {e}")
            logger.info("Attempting to start LM Studio...")
            return self._start_lm_studio_and_load_model()

    def _load_model_in_lm_studio(self) -> bool:
        """Attempt to load the model in LM Studio via API."""
        try:
            # Try to load the model using LM Studio's load endpoint
            load_payload = {
                "model": self.model_name
            }

            load_response = self.session.post(
                f"{self.api_url}/v1/models/load",
                json=load_payload,
                timeout=60  # Model loading can take time
            )

            if load_response.status_code == 200:
                logger.info(f"Successfully loaded model {self.model_name} in LM Studio")
                self.is_loaded = True
                return True
            else:
                logger.warning(f"Failed to load model via API: {load_response.status_code}")
                return False

        except Exception as e:
            logger.warning(f"Failed to load model via API: {e}")
            return False

    def _start_lm_studio_and_load_model(self) -> bool:
        """Attempt to start LM Studio and load the model."""
        try:
            import subprocess
            import time

            # Try to start LM Studio (this is platform-specific)
            logger.info("Attempting to start LM Studio...")

            # Common LM Studio installation paths
            lm_studio_paths = [
                "/Applications/LM Studio.app/Contents/MacOS/LM Studio",  # macOS
                "C:\\Users\\%USERNAME%\\AppData\\Local\\LMStudio\\LM Studio.exe",  # Windows
                "/usr/local/bin/lmstudio",  # Linux
                "/opt/lmstudio/lmstudio"   # Linux alternative
            ]

            started = False
            for path in lm_studio_paths:
                try:
                    subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    logger.info(f"Started LM Studio from {path}")
                    started = True
                    break
                except (FileNotFoundError, OSError):
                    continue

            if not started:
                logger.warning("Could not automatically start LM Studio. Please start it manually.")
                return False

            # Wait for LM Studio to start
            logger.info("Waiting for LM Studio to initialize...")
            for attempt in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                try:
                    test_response = self.session.get(f"{self.api_url}/v1/models", timeout=5)
                    if test_response.status_code == 200:
                        logger.info("LM Studio is now running")
                        return self._load_model_in_lm_studio()
                except:
                    continue

            logger.error("LM Studio did not start within 30 seconds")
            return False

        except Exception as e:
            logger.error(f"Failed to start LM Studio: {e}")
            return False

    def generate_description(
        self,
        image: Image.Image,
        context: str = "",
        max_length: int = 100
    ) -> Tuple[str, float]:
        """
        Generate description using Gemma-3n-e4b via LM Studio.

        Args:
            image: PIL Image object
            context: Context text from surrounding content
            max_length: Maximum description length

        Returns:
            Tuple of (description, confidence_score)
        """
        if not self.is_loaded or not self.session:
            logger.error("Gemma model not loaded")
            return "Image description unavailable (model not loaded)", 0.0

        try:
            import base64
            import io

            # Convert PIL image to base64
            buffer = io.BytesIO()
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize if too large (for efficiency)
            max_size = 768
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            image.save(buffer, format='JPEG', quality=85)
            image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Craft prompt for brief, TTS-friendly descriptions
            system_prompt = """You are an expert at describing images for audiobook narration.
            Generate brief, clear descriptions that work well when read aloud.
            Keep descriptions under 50 words.
            Focus on the most important visual elements.
            Be descriptive but concise.
            Avoid technical jargon.
            Use natural, flowing language."""

            user_prompt = f"""Describe this image briefly for an audiobook listener.
            Context: {context[:200] if context else 'No additional context provided.'}

            Provide a clear, concise description in under 50 words that captures the essential visual information."""

            # Prepare the API request
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 150,
                "temperature": 0.7,
                "top_p": 0.9
            }

            # Make the API request with longer timeout for complex processing
            response = self.session.post(
                self.api_endpoint,
                json=payload,
                timeout=60,  # Increased to 60 seconds for complex image processing
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                description = result['choices'][0]['message']['content'].strip()

                # Post-process the description
                description = self._clean_description(description, max_length)

                # Calculate confidence based on response quality
                confidence = self._calculate_confidence(description, result)

                logger.debug(f"Gemma description generated: '{description[:50]}...' (confidence: {confidence:.2f})")
                return description, confidence

            else:
                logger.error(f"Gemma API request failed: {response.status_code} - {response.text}")
                return f"Error generating description: API request failed", 0.0

        except Exception as e:
            logger.error(f"Error generating Gemma description: {e}")
            return f"Error generating description: {str(e)}", 0.0

    def _clean_description(self, description: str, max_length: int) -> str:
        """Clean and optimize description for TTS."""
        # Remove quotes and problematic characters
        description = description.strip('"\'')

        # Ensure proper sentence structure
        if description and not description.endswith(('.', '!', '?')):
            description += '.'

        # Capitalize first letter
        if description:
            description = description[0].upper() + description[1:]

        # Remove problematic characters for TTS
        description = description.replace('"', '').replace("'", "")

        # Truncate if too long
        if len(description) > max_length:
            # Find last complete sentence within limit
            sentences = description.split('.')
            result = ""
            for sentence in sentences:
                if len(result + sentence + '.') <= max_length:
                    result += sentence + '.'
                else:
                    break
            description = result.rstrip('.')
            if description and not description.endswith(('.', '!', '?')):
                description += '.'

        return description

    def _calculate_confidence(self, description: str, api_result: dict) -> float:
        """Calculate confidence score based on description quality."""
        base_confidence = 0.8  # Base confidence for successful API call

        # Reduce confidence for very short descriptions
        if len(description) < 20:
            base_confidence -= 0.2

        # Reduce confidence for error messages
        if "error" in description.lower() or "unavailable" in description.lower():
            base_confidence = 0.1

        # Check for finish_reason
        finish_reason = api_result.get('choices', [{}])[0].get('finish_reason', '')
        if finish_reason == 'length':
            base_confidence -= 0.1  # Description was truncated

        return max(0.0, min(1.0, base_confidence))

    def unload_model(self) -> None:
        """Clean up resources."""
        if self.session:
            self.session.close()
            self.session = None
        self.is_loaded = False


class ImageDescriptionPipeline:
    """
    Local VLM pipeline for image description generation.
    """

    def __init__(self, config: ImageConfig, cache_dir: Optional[Path] = None, progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize image description pipeline.

        Args:
            config: Image processing configuration
            cache_dir: Optional cache directory path
            progress_tracker: Optional progress tracking system
        """
        self.config = config
        self.cache_dir = cache_dir or Path(".vlm_cache")
        self.cache = ImageDescriptionCache(self.cache_dir)
        self.model: Optional[BaseVLMModel] = None
        self.progress_tracker = progress_tracker

        logger.info(f"Initializing VLM pipeline with model: {config.model}")
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the VLM model."""
        try:
            model_name = self.config.model.lower()

            if "gemma" in model_name:
                # Initialize Gemma model with LM Studio
                api_url = getattr(self.config, 'api_url', 'http://127.0.0.1:1234')
                self.model = GemmaVLMModel(self.config.model, api_url)
                logger.info("Initializing Gemma VLM model via LM Studio")
            elif "llava" in model_name:
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

        # Emit start event
        if self.progress_tracker:
            self.progress_tracker.emit_event(create_start_event(
                PipelineType.IMAGE,
                total_items=1,
                current_item=Path(image_path).name
            ))

        # Check cache first
        if not force_regenerate:
            cached_description = self.cache.get(image_path, context)
            if cached_description:
                # Emit completion event for cache hit
                if self.progress_tracker:
                    self.progress_tracker.emit_event(create_complete_event(
                        PipelineType.IMAGE,
                        current_item=Path(image_path).name,
                        cache_hit=True
                    ))
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

            # Emit completion event
            if self.progress_tracker:
                self.progress_tracker.emit_event(create_complete_event(
                    PipelineType.IMAGE,
                    current_item=Path(image_path).name,
                    processing_time=processing_time,
                    description_length=len(description_text),
                    confidence=confidence
                ))

            return description

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")

            # Emit error event
            if self.progress_tracker:
                self.progress_tracker.emit_event(create_error_event(
                    PipelineType.IMAGE,
                    error_message=str(e),
                    current_item=Path(image_path).name
                ))

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

        # Emit start event for batch processing
        if self.progress_tracker:
            self.progress_tracker.emit_event(create_start_event(
                PipelineType.IMAGE,
                total_items=len(image_list),
                current_item=f"Batch processing {len(image_list)} images"
            ))

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

                        # Emit progress event
                        if self.progress_tracker:
                            self.progress_tracker.emit_event(create_progress_event(
                                PipelineType.IMAGE,
                                completed_items=len(descriptions),
                                total_items=len(image_list),
                                current_item=f"Processed {len(descriptions)}/{len(image_list)} images",
                                custom_stats={'cache_hits': cache_hits}
                            ))

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

                # Emit progress event
                if self.progress_tracker:
                    self.progress_tracker.emit_event(create_progress_event(
                        PipelineType.IMAGE,
                        completed_items=len(descriptions),
                        total_items=len(image_list),
                        current_item=f"Processed {len(descriptions)}/{len(image_list)} images",
                        custom_stats={'cache_hits': cache_hits}
                    ))

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


def create_image_pipeline(config: ImageConfig, progress_tracker: Optional[ProgressTracker] = None) -> ImageDescriptionPipeline:
    """
    Factory function to create image description pipeline.

    Args:
        config: Image processing configuration
        progress_tracker: Optional progress tracking system

    Returns:
        Initialized image description pipeline
    """
    return ImageDescriptionPipeline(config, progress_tracker=progress_tracker)