# Project TODOs

## High Priority

- [ ] **Expand test coverage for OmniParser integration**
  - Add unit tests for EPUB parsing edge cases
  - Add integration tests for TOC extraction
  - Verify checkpoint/resume functionality

- [ ] **Document ClaudeUsage workflow guides integration**
  - Review and adapt BaseProject workflows for epub2tts specifics
  - Add project-specific examples to relevant guides
  - Update team on new documentation structure

## Medium Priority

- [ ] **Performance optimization for large EPUBs**
  - Profile memory usage for files >100MB
  - Optimize image processing pipeline for batch operations
  - Consider chunked processing for very large books

- [ ] **Enhance error handling and recovery**
  - Add more granular error messages for TTS failures
  - Implement retry logic for API-based TTS engines
  - Improve checkpoint granularity for long-running processes

## Low Priority / Future Ideas

- [ ] **Additional TTS engine integrations**
  - Research and evaluate OpenAI TTS
  - Consider Azure Speech Services integration
  - Evaluate cost/quality trade-offs for each engine

- [ ] **Web interface for batch processing**
  - Design simple web UI for EPUB uploads
  - Add progress tracking dashboard
  - Implement job queue management

## Completed

- [x] Integrate BaseProject template structure (2025-10-29)
- [x] Add ClaudeUsage/ workflow documentation (2025-10-29)
- [x] Enhance CLAUDE.md with project context (2025-10-29)

---

*Last updated: 2025-10-29*
