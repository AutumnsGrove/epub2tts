"""
Modern text processing pipeline using spaCy, clean-text, and LangChain.

This module provides production-scale text processing that replaces regex-based
approaches with intelligent NLP-driven processing.
"""

import logging
import spacy
from cleantext import clean
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import re
import ftfy

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    SpacyTextSplitter,
    MarkdownTextSplitter
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistics from modern text processing."""
    original_length: int
    processed_length: int
    chapters_detected: int
    chunks_created: int
    spacy_processing_time: float
    confidence_score: float

    @property
    def compression_ratio(self) -> float:
        """Calculate text compression ratio."""
        if self.original_length == 0:
            return 0.0
        return self.processed_length / self.original_length


@dataclass
class SmartChapter:
    """Enhanced chapter with semantic information."""
    chapter_num: int
    title: str
    content: str
    word_count: int
    estimated_duration: float
    confidence: float
    semantic_summary: Optional[str] = None
    topics: List[str] = None
    named_entities: List[Tuple[str, str]] = None  # (entity, label)
    chunks: List[Dict[str, Any]] = None  # For TTS processing


class ModernTextProcessor:
    """
    Modern text processor using spaCy, clean-text, and LangChain splitters.

    Replaces regex-based processing with intelligent NLP-driven approaches
    for production-scale performance with 100k+ word documents.
    """

    def __init__(self, model_name: str = "en_core_web_sm", chunk_size: int = 4000):
        """
        Initialize modern text processor.

        Args:
            model_name: spaCy model to load
            chunk_size: Target chunk size for text splitting
        """
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.nlp = None
        self.text_splitter = None
        self.stats = ProcessingStats(0, 0, 0, 0, 0.0, 0.0)

        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize spaCy and text splitting components."""
        try:
            # Load spaCy model
            self.nlp = spacy.load(self.model_name)

            # Add custom pipeline components for chapter detection (simplified)
            # Store patterns for later use instead of adding to pipeline
            self.chapter_patterns = self._get_chapter_patterns()

            # Initialize text splitters
            self.semantic_splitter = SpacyTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=200
            )

            self.recursive_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=200,
                separators=["\n\n\n", "\n\n", "\n", ". ", " ", ""]
            )

            logger.info(f"Initialized modern text processor with {self.model_name}")

        except Exception as e:
            logger.error(f"Failed to initialize text processor: {e}")
            raise RuntimeError(f"Cannot initialize modern text processor: {e}")

    def process_text(self, text: str, use_toc: Optional[List[Dict]] = None) -> List[SmartChapter]:
        """
        Process text with modern NLP pipeline.

        Args:
            text: Raw text to process
            use_toc: Optional table of contents for chapter boundaries

        Returns:
            List of SmartChapter objects with enhanced metadata
        """
        import time
        start_time = time.time()

        self.stats = ProcessingStats(len(text), 0, 0, 0, 0.0, 0.0)

        try:
            # Step 1: Clean text with clean-text library
            cleaned_text = self._clean_text_modern(text)

            # Step 2: Use TOC if available, otherwise intelligent detection
            if use_toc:
                chapters = self._extract_chapters_from_toc(cleaned_text, use_toc)
            else:
                chapters = self._detect_chapters_intelligent(cleaned_text)

            # Step 3: Process each chapter with spaCy
            processed_chapters = []
            for chapter in chapters:
                smart_chapter = self._enhance_chapter_with_nlp(chapter)
                processed_chapters.append(smart_chapter)

            # Step 4: Create semantic chunks for TTS
            for chapter in processed_chapters:
                chapter.chunks = self._create_semantic_chunks(chapter.content)

            # Update stats
            self.stats.processed_length = sum(len(ch.content) for ch in processed_chapters)
            self.stats.chapters_detected = len(processed_chapters)
            self.stats.chunks_created = sum(len(ch.chunks) for ch in processed_chapters)
            self.stats.spacy_processing_time = time.time() - start_time
            self.stats.confidence_score = sum(ch.confidence for ch in processed_chapters) / len(processed_chapters)

            logger.info(
                f"Modern text processing completed: "
                f"{self.stats.chapters_detected} chapters, "
                f"{self.stats.chunks_created} chunks, "
                f"{self.stats.spacy_processing_time:.2f}s processing time"
            )

            return processed_chapters

        except Exception as e:
            logger.error(f"Error in modern text processing: {e}")
            raise

    def _clean_text_modern(self, text: str) -> str:
        """
        Clean text using clean-text library for TTS optimization.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text optimized for TTS
        """
        # First fix encoding issues
        text = ftfy.fix_text(text)

        # Use clean-text with TTS-specific settings
        cleaned = clean(
            text,
            fix_unicode=True,
            to_ascii=False,  # Keep Unicode for proper pronunciation
            lower=False,  # Preserve case for proper nouns
            no_line_breaks=False,  # Keep structure
            no_urls=True,
            no_emails=True,
            no_phone_numbers=True,
            no_numbers=False,  # Keep numbers for reading
            no_digits=False,
            no_currency_symbols=False,  # Will handle separately
            no_punct=False,  # Keep punctuation for pauses
            replace_with_url="URL",
            replace_with_email="email address",
            replace_with_phone_number="phone number",
            lang="en"
        )

        # Apply TTS-specific normalizations
        cleaned = self._normalize_for_tts(cleaned)

        return cleaned

    def _normalize_for_tts(self, text: str) -> str:
        """
        Apply TTS-specific text normalizations.

        Args:
            text: Text to normalize

        Returns:
            TTS-optimized text
        """
        # Currency symbols
        text = re.sub(r'\$(\d+)', r'\1 dollars', text)
        text = re.sub(r'€(\d+)', r'\1 euros', text)
        text = re.sub(r'£(\d+)', r'\1 pounds', text)

        # Percentages
        text = re.sub(r'(\d+)%', r'\1 percent', text)

        # Ampersands
        text = re.sub(r'\s&\s', ' and ', text)

        # Smart quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Em/en dashes
        text = text.replace('—', ' -- ').replace('–', ' - ')

        # Ellipsis handling
        text = text.replace('…', '... ')

        # Multiple spaces
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _extract_chapters_from_toc(self, text: str, toc: List[Dict]) -> List[SmartChapter]:
        """
        Extract chapters using TOC structure.

        Args:
            text: Full text content
            toc: Table of contents structure

        Returns:
            List of chapters based on TOC
        """
        chapters = []

        for i, entry in enumerate(toc):
            title = entry.get('title', f'Chapter {i+1}')

            # Try to find content boundaries
            if 'content' in entry:
                content = entry['content']
            else:
                # Extract content between TOC entries
                content = self._extract_content_by_title(text, title, toc, i)

            if content and content.strip():
                chapter = SmartChapter(
                    chapter_num=i + 1,
                    title=title,
                    content=content.strip(),
                    word_count=len(content.split()),
                    estimated_duration=len(content.split()) / 200.0,  # 200 wpm
                    confidence=1.0,  # High confidence with TOC
                    topics=[],
                    named_entities=[],
                    chunks=[]
                )
                chapters.append(chapter)

        return chapters

    def _extract_content_by_title(self, text: str, title: str, toc: List[Dict], current_index: int) -> str:
        """
        Extract content between chapter titles.

        Args:
            text: Full text
            title: Current chapter title
            toc: Full TOC
            current_index: Current chapter index

        Returns:
            Chapter content
        """
        # Find start position
        title_patterns = [
            re.escape(title),
            re.escape(title.upper()),
            re.escape(title.lower()),
            r'^\s*' + re.escape(title) + r'\s*$'
        ]

        start_pos = 0
        for pattern in title_patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                start_pos = match.end()
                break

        # Find end position (next chapter or end of text)
        end_pos = len(text)
        if current_index + 1 < len(toc):
            next_title = toc[current_index + 1].get('title', '')
            for pattern in [re.escape(next_title), re.escape(next_title.upper())]:
                match = re.search(pattern, text[start_pos:], re.MULTILINE | re.IGNORECASE)
                if match:
                    end_pos = start_pos + match.start()
                    break

        return text[start_pos:end_pos]

    def _detect_chapters_intelligent(self, text: str) -> List[SmartChapter]:
        """
        Detect chapters using spaCy's intelligent NLP analysis.

        Args:
            text: Text to analyze

        Returns:
            List of detected chapters
        """
        chapters = []

        # Process text with spaCy
        doc = self.nlp(text)

        # Look for chapter-like structures using NLP
        chapter_candidates = []

        # Method 1: Look for sentences that start with chapter-like patterns
        for sent in doc.sents:
            sent_text = sent.text.strip()

            # Check if sentence looks like a chapter heading
            if self._is_chapter_heading(sent_text, sent):
                chapter_candidates.append({
                    'start': sent.start_char,
                    'end': sent.end_char,
                    'title': sent_text,
                    'confidence': self._calculate_chapter_confidence(sent_text, sent)
                })

        # Method 2: Look for structural patterns (large gaps, formatting)
        chapter_candidates.extend(self._detect_structural_chapters(text, doc))

        # Sort by position and filter
        chapter_candidates.sort(key=lambda x: x['start'])
        chapter_candidates = self._filter_chapter_candidates(chapter_candidates)

        # Extract content between chapters
        for i, candidate in enumerate(chapter_candidates):
            start_pos = candidate['end']
            end_pos = chapter_candidates[i + 1]['start'] if i + 1 < len(chapter_candidates) else len(text)

            content = text[start_pos:end_pos].strip()

            if content:
                chapter = SmartChapter(
                    chapter_num=i + 1,
                    title=candidate['title'],
                    content=content,
                    word_count=len(content.split()),
                    estimated_duration=len(content.split()) / 200.0,
                    confidence=candidate['confidence'],
                    topics=[],
                    named_entities=[],
                    chunks=[]
                )
                chapters.append(chapter)

        # Fallback: if no chapters detected, create one large chapter
        if not chapters:
            chapter = SmartChapter(
                chapter_num=1,
                title="Full Document",
                content=text,
                word_count=len(text.split()),
                estimated_duration=len(text.split()) / 200.0,
                confidence=0.5,
                topics=[],
                named_entities=[],
                chunks=[]
            )
            chapters.append(chapter)

        return chapters

    def _is_chapter_heading(self, text: str, sent_doc) -> bool:
        """Check if text looks like a chapter heading using NLP."""
        text_lower = text.lower()

        # Check if matches our chapter patterns
        for pattern in self.chapter_patterns:
            if re.match(pattern, text_lower):
                return True

        # Check linguistic features
        if len(text.split()) <= 10:  # Short enough to be a heading
            # Check if it's title case or all caps
            if text.istitle() or text.isupper():
                return True

            # Check if it contains proper nouns (potential title)
            if sent_doc and any(token.pos_ == "PROPN" for token in sent_doc):
                return True

        return False

    def _calculate_chapter_confidence(self, text: str, sent_doc) -> float:
        """Calculate confidence that text is a chapter heading."""
        confidence = 0.5  # Base confidence

        text_lower = text.lower()

        # Boost for explicit chapter words
        if 'chapter' in text_lower:
            confidence += 0.3
        if 'part' in text_lower or 'section' in text_lower:
            confidence += 0.2

        # Boost for numbers
        if re.search(r'\d+', text):
            confidence += 0.1

        # Boost for short length
        if len(text.split()) <= 5:
            confidence += 0.1

        # Boost for title case
        if text.istitle():
            confidence += 0.1

        return min(confidence, 1.0)

    def _detect_structural_chapters(self, text: str, doc) -> List[Dict]:
        """Detect chapters based on structural patterns."""
        candidates = []

        # Look for large paragraph breaks
        paragraphs = text.split('\n\n')

        for i, para in enumerate(paragraphs):
            para = para.strip()
            if para and len(para.split()) <= 10:  # Short paragraph
                # Check if next paragraph is substantial
                if i + 1 < len(paragraphs) and len(paragraphs[i + 1].split()) > 50:
                    # Find position in original text
                    pos = text.find(para)
                    if pos >= 0:
                        candidates.append({
                            'start': pos,
                            'end': pos + len(para),
                            'title': para,
                            'confidence': 0.6
                        })

        return candidates

    def _filter_chapter_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """Filter and refine chapter candidates."""
        if not candidates:
            return candidates

        # Remove duplicates and low confidence
        filtered = []
        for candidate in candidates:
            if candidate['confidence'] >= 0.6:
                # Check if too close to existing candidate
                too_close = False
                for existing in filtered:
                    if abs(candidate['start'] - existing['start']) < 100:
                        if candidate['confidence'] > existing['confidence']:
                            filtered.remove(existing)
                        else:
                            too_close = True
                        break

                if not too_close:
                    filtered.append(candidate)

        return filtered

    def _enhance_chapter_with_nlp(self, chapter: SmartChapter) -> SmartChapter:
        """Enhance chapter with NLP analysis."""
        doc = self.nlp(chapter.content)

        # Extract named entities
        chapter.named_entities = [(ent.text, ent.label_) for ent in doc.ents]

        # Extract key topics (simple approach using noun phrases)
        noun_phrases = [chunk.text for chunk in doc.noun_chunks]
        # Get most common noun phrases as topics
        from collections import Counter
        topic_counts = Counter(noun_phrases)
        chapter.topics = [topic for topic, count in topic_counts.most_common(5)]

        # Generate semantic summary (first and last sentences)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        if sentences:
            if len(sentences) == 1:
                chapter.semantic_summary = sentences[0]
            else:
                chapter.semantic_summary = f"{sentences[0]} ... {sentences[-1]}"

        return chapter

    def _create_semantic_chunks(self, content: str) -> List[Dict[str, Any]]:
        """Create semantic chunks for TTS processing."""
        chunks = []

        # Try semantic splitter first
        try:
            semantic_chunks = self.semantic_splitter.split_text(content)

            for i, chunk in enumerate(semantic_chunks):
                chunks.append({
                    'id': f'semantic_{i:03d}',
                    'text': chunk,
                    'method': 'semantic',
                    'word_count': len(chunk.split())
                })

        except Exception as e:
            logger.warning(f"Semantic splitting failed: {e}, falling back to recursive")

            # Fallback to recursive splitter
            recursive_chunks = self.recursive_splitter.split_text(content)

            for i, chunk in enumerate(recursive_chunks):
                chunks.append({
                    'id': f'recursive_{i:03d}',
                    'text': chunk,
                    'method': 'recursive',
                    'word_count': len(chunk.split())
                })

        return chunks

    def _get_chapter_patterns(self) -> List[str]:
        """Get patterns for chapter detection."""
        return [
            r"^Chapter\s+\d+",
            r"^Chapter\s+[IVX]+",
            r"^CHAPTER\s+\d+",
            r"^Part\s+[IVX\d]+",
            r"^Section\s+[IVX\d]+",
            r"^\d+\.\s+[A-Z]",
        ]

    def get_processing_stats(self) -> ProcessingStats:
        """Get statistics from the last processing operation."""
        return self.stats


# Custom chapter detection using direct pattern matching
# (Removed complex spaCy component approach for simplicity)