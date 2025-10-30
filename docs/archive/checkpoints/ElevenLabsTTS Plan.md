ElevenLabs TTS Integration Plan for epub2tts

     Overview

     Add support for ElevenLabs TTS models via API as an alternative to the default Kokoro model. Users can enable ElevenLabs by adding an API key to a new secrets configuration system.

     Implementation Steps

     1. Create Secrets Management System

     - Create secrets.json file with ElevenLabs API key support
     - Add secrets_template.json as an example for users
     - Update .gitignore to exclude secrets.json
     - Create secrets loader utility in src/utils/secrets.py

     2. Add ElevenLabs TTS Engine

     - Create src/pipelines/elevenlabs_tts.py implementing ElevenLabsTTSPipeline class
     - Implement voice synthesis using ElevenLabs API
     - Support voice selection from available ElevenLabs voices
     - Handle API rate limiting and error responses
     - Implement chunking for long text (ElevenLabs has character limits)

     3. Update Configuration System

     - Extend TTSConfig dataclass in src/utils/config.py to include:
       - engine: "kokoro" or "elevenlabs" (default: "kokoro")
       - elevenlabs_voice_id: Default voice ID for ElevenLabs
       - elevenlabs_model: Model selection (e.g., "eleven_monolingual_v1")
       - elevenlabs_stability: Voice stability setting (0.0-1.0)
       - elevenlabs_similarity_boost: Voice similarity boost (0.0-1.0)
     - Update default_config.yaml with ElevenLabs settings

     4. Create TTS Factory Pattern

     - Modify tts_pipeline.py to act as a factory
     - Add engine selection logic in create_tts_pipeline():
       - Check for ElevenLabs API key in secrets
       - Fall back to Kokoro if no key found
       - Allow manual override via config
     - Create common TTS interface that both engines implement

     5. Update Dependencies

     - Add elevenlabs package to pyproject.toml and requirements.txt
     - Update UV lock file after adding new dependency

     6. Add Tests

     - Create mock tests for ElevenLabs integration
     - Test API key loading from secrets
     - Test fallback to Kokoro when no API key present
     - Test voice selection and synthesis parameters

     7. Update Documentation

     - Create checkpoint file documenting the implementation
     - Update README with ElevenLabs setup instructions
     - Document voice IDs and available models

     File Structure Changes

     epub2tts/
     ├── secrets.json (new, gitignored)
     ├── secrets_template.json (new)
     ├── src/
     │   ├── utils/
     │   │   ├── secrets.py (new)
     │   │   └── config.py (modified)
     │   └── pipelines/
     │       ├── tts_pipeline.py (modified - factory pattern)
     │       ├── elevenlabs_tts.py (new)
     │       └── kokoro_tts.py (refactored from tts_pipeline.py)
     ├── config/
     │   └── default_config.yaml (modified)
     ├── tests/
     │   └── test_elevenlabs_tts.py (new)
     └── checkpoints/
         └── ELEVENLABS_INTEGRATION_2025-09-28.md (new)

     Implementation Details

     Secrets Structure

     {
       "elevenlabs_api_key": "your-api-key-here",
       "comment": "Add your ElevenLabs API key here. Keep this file private."
     }

     Config Addition

     tts:
       engine: "kokoro"  # or "elevenlabs"
       
       # ElevenLabs specific settings
       elevenlabs:
         voice_id: "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
         model: "eleven_monolingual_v1"
         stability: 0.75
         similarity_boost: 0.75
         optimize_streaming_latency: 2

     Usage Flow

     1. User adds ElevenLabs API key to secrets.json
     2. User optionally configures voice settings in config
     3. System automatically detects API key and enables ElevenLabs
     4. Falls back to Kokoro if API key missing or API errors occur

     Benefits

     - Choice of TTS engines - Users can choose based on quality/cost preferences
     - Seamless fallback - Works without API key using Kokoro
     - Professional voices - Access to ElevenLabs' high-quality voices
     - Maintains compatibility - Existing Kokoro setup remains default