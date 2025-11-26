# epub2tts TODO

## Future Enhancements

### Pause/Pacing System for Natural Audiobook Flow
**Priority:** Low (requires TTS model changes)

The text cleaner currently inserts `[PAUSE: X]` markers for natural speech pacing:
- After sentences, paragraphs, chapters
- After questions and exclamations
- Between dialogue

**Current state:** Markers are stripped before TTS because Kokoro doesn't support SSML.

**Future approach options:**
1. **Post-processing silence injection** - After generating audio, insert silence at marker positions
2. **Switch to SSML-capable TTS** - ElevenLabs, Azure, Google Cloud TTS support `<break time="Xs"/>`
3. **Fine-tune Kokoro** - Train on audiobook data with natural pacing
4. **Hybrid approach** - Generate audio per-sentence, concatenate with configurable gaps

**Related files:**
- `src/core/text_cleaner.py` - `add_pause_markers()` method
- `src/pipelines/tts_pipeline.py` - `_preprocess_text()` strips markers
- `config/regex_patterns.yaml` - `pause_rules` configuration
