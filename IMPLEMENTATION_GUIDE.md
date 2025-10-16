# epub2tts Web Reader - Implementation Guide

**Date Created:** October 16, 2025
**Status:** Ready for Implementation
**Phase:** Planning Complete

---

## Overview

This guide provides the complete roadmap for transforming epub2tts into a dual-mode (CLI + Web) application with clean architectural separation. All planning documents have been created and are ready for implementation via Task agents.

---

## Created Documents

### ✅ Specification Documents

1. **WEB_READER_PROJECT_SPEC_v2.md** (41 KB)
   - Updated project specification with new architecture
   - Clean separation: Omniparser, /core/, /audio-processing/, /web/, /cli/
   - Desktop-first web interface with mobile accessibility
   - Abstract TTS interface (Kokoro, ElevenLabs, Hume-ready)
   - Complete MVP implementation details

2. **OMNIPARSER_PROJECT_SPEC.md** (36 KB)
   - Standalone universal document parser specification
   - Support for EPUB, PDF, DOCX, HTML, URLs, Markdown, Text
   - Clean API: `parse_document(path) -> Document`
   - PyPI-ready package configuration
   - Comprehensive testing strategy

### ✅ Implementation Metaprompts

3. **METAPROMPT_1_OMNIPARSER_EXTRACTION.md** (21 KB)
   - Step-by-step guide for creating Omniparser package
   - 16 phases from setup to validation
   - Port existing EPUB logic + add new parsers
   - Comprehensive testing requirements
   - Success criteria and validation checklist

4. **METAPROMPT_2_REPO_REORGANIZATION.md** (31 KB)
   - Detailed reorganization of epub2tts repository
   - 18 phases from structure creation to final validation
   - Abstract audio interface implementation
   - CLI preservation with new structure
   - Complete import updates and testing

5. **METAPROMPT_3_WEBGPU_RESEARCH.md** (25 KB)
   - Comprehensive WebGPU feasibility research plan
   - 10 research sections covering all aspects
   - Decision matrix for MVP/Post-MVP/Skip
   - Expected output format with examples
   - Research tools and resources

---

## Architecture Summary

### New Structure

```
epub2tts/                           # Main repository
├── cli/                            # CLI interface (preserved)
├── core/                           # Pipeline orchestration (NEW)
├── audio_processing/               # TTS engines (NEW)
├── web/                            # Web interface (NEW)
│   ├── backend/                    # FastAPI
│   └── frontend/                   # Vanilla JS
├── text/                           # Text processing (existing)
├── utils/                          # Utilities (existing)
└── tests/                          # Tests (reorganized)

omniparser/                         # Separate repository
├── src/
│   └── omniparser/
│       ├── parsers/                # Format-specific parsers
│       ├── processors/             # Post-processing
│       └── utils/                  # Utilities
└── tests/
```

### Key Principles

1. **Separation of Concerns:**
   - Parsing: Omniparser (external)
   - Orchestration: /core/
   - Audio: /audio-processing/ (abstract interface)
   - UI: /cli/ and /web/

2. **Abstract Interfaces:**
   - `BaseTTSEngine` for all audio engines
   - Easy addition of new engines (Hume: just implement interface)
   - Factory pattern for engine selection

3. **Dual Mode:**
   - CLI: All existing functionality preserved
   - Web: New interface sharing same core

---

## Implementation Sequence

### Phase 1: Omniparser Creation (Week 1)
**Use:** METAPROMPT_1_OMNIPARSER_EXTRACTION.md

**Task Agent Invocation:**
```bash
# Start with Task agent (general-purpose)
Task agent with prompt from METAPROMPT_1_OMNIPARSER_EXTRACTION.md
```

**Key Steps:**
1. Create new repository structure
2. Port existing EPUB logic from epub2tts
3. Implement new parsers (PDF, DOCX, HTML, etc.)
4. Comprehensive testing (>80% coverage)
5. PyPI package setup

**Success Criteria:**
- All tests pass
- Package builds successfully
- Can install: `uv add omniparser`
- Example usage works

**Validation Statement Required:**
> "Omniparser extraction is COMPLETE. All tests pass. Package builds successfully. Ready for epub2tts integration."

---

### Phase 2: Repository Reorganization (Week 1-2)
**Use:** METAPROMPT_2_REPO_REORGANIZATION.md

**Prerequisites:**
- ✅ Phase 1 complete and validated
- ✅ Omniparser package available

**Task Agent Invocation:**
```bash
# Sequential Task agent calls
Task agent with prompt from METAPROMPT_2_REPO_REORGANIZATION.md
```

**Key Steps:**
1. Create new directory structure
2. Implement abstract audio interface
3. Port TTS engines to new structure
4. Move core components
5. Update CLI for new structure
6. Remove old files
7. Update all tests

**Success Criteria:**
- All existing tests pass
- CLI works identically to before
- New structure is clean
- Documentation updated

**Validation Statement Required:**
> "Repository reorganization is COMPLETE. All tests pass. CLI works identically. Architecture is clean. Ready for web development."

---

### Phase 3: WebGPU Research (Parallel)
**Use:** METAPROMPT_3_WEBGPU_RESEARCH.md

**Task Agent Invocation:**
```bash
# Separate chat with house-research agent
house-research agent with prompt from METAPROMPT_3_WEBGPU_RESEARCH.md
```

**Key Sections:**
1. Browser support analysis (2025)
2. ONNX Runtime Web + WebGPU
3. Model conversion pipeline
4. Performance benchmarks
5. Kokoro-specific considerations
6. Alternative approaches
7. Implementation complexity
8. Competitive analysis
9. Caching strategy
10. User experience design

**Deliverable:**
- Comprehensive research report
- Clear recommendation: Include in MVP / Post-MVP / Skip
- Decision matrix with weighted scores
- Implementation plan (if recommended)
- Fallback strategy

**Use Report For:**
- Deciding whether to include WebGPU in MVP
- Understanding risks and complexity
- Planning progressive enhancement
- Designing fallback UX

---

### Phase 4: Web Backend Development (Weeks 2-3)
**Prerequisites:**
- ✅ Phase 2 complete and validated
- ✅ Phase 3 research reviewed

**Components to Build:**
1. FastAPI application structure
2. Database schema (SQLite async)
3. Document upload router (integrates Omniparser)
4. TTS generation router (wraps audio_processing)
5. Reading position endpoints
6. WebSocket manager (real-time updates)

**Task Agent Usage:**
- Separate Task agent for each major component
- Use web-research-specialist for FastAPI best practices
- Use house-bash for testing

**Success Criteria:**
- API endpoints functional
- WebSocket communication works
- Integration with core pipeline successful
- All API tests pass

---

### Phase 5: Web Frontend Development (Weeks 4-5)
**Prerequisites:**
- ✅ Phase 4 complete

**Components to Build:**
1. Upload zone (drag-and-drop)
2. Reader view (Web Component with word highlighting)
3. Audio player (custom controls)
4. Table of contents drawer
5. Settings panel (voice, speed, etc.)
6. State management

**Task Agent Usage:**
- Separate Task agent for each Web Component
- Desktop-first, responsive CSS
- Test on multiple browsers

**Success Criteria:**
- Upload → process → play flow works
- Word highlighting syncs with audio
- Desktop browsers fully functional
- Mobile browsers accessible

---

### Phase 6: Integration & MVP (Week 6)
**Components:**
1. End-to-end integration testing
2. Performance optimization
3. Bug fixes
4. Documentation
5. Deployment guide

**Success Criteria:**
- ✅ Full user flow works
- ✅ Desktop experience polished
- ✅ Mobile experience accessible
- ✅ Documentation complete
- ✅ Ready for deployment

---

## Using the Metaprompts

### For Task Agents (General-Purpose)

**Pattern:**
```
You are implementing [component] for the epub2tts project.

[Full metaprompt text]

Current phase: [X]
Prerequisites verified: [list]

Implement this phase and validate before proceeding.
```

**Key Points:**
- Each metaprompt is designed for sequential execution
- Validation is required at each phase
- Don't skip phases or validation
- Report completion with validation statement

### For House-Research Agent

**Pattern:**
```
You are researching WebGPU feasibility for browser-based TTS.

[Full METAPROMPT_3 text]

Research all sections thoroughly and produce a comprehensive report
with clear recommendations.
```

**Key Points:**
- Run in separate chat session
- Take time for thorough research
- Cite all sources
- Provide actionable recommendations

---

## Key Decisions Made

### 1. Omniparser as Separate Repository ✅
- **Rationale:** Reusable by other projects, independent updates
- **Approach:** PyPI package, clean API
- **Status:** Spec complete, ready for implementation

### 2. Abstract Audio Interface ✅
- **Rationale:** Easy addition of Hume and future engines
- **Design:** Factory pattern, async interface
- **Status:** Spec complete, ready for implementation

### 3. Web in Main Repository ✅
- **Rationale:** Dual-mode in single repo
- **Structure:** /web/ subdirectory
- **Status:** Structure defined, ready for implementation

### 4. Desktop-First Web UI ✅
- **Rationale:** Easier development, web = mobile accessible
- **Approach:** Responsive CSS, mobile testing later
- **Status:** Strategy defined

### 5. Kokoro MVP, WebGPU Research ✅
- **Rationale:** Server-side proven, WebGPU high-risk
- **Approach:** Research first, decide based on findings
- **Status:** Research metaprompt ready

### 6. Hume Engine Stub ✅
- **Rationale:** Abstract interface ready, easy to add
- **Approach:** Placeholder with clear interface
- **Status:** Design complete

---

## Success Metrics

### MVP Success Criteria (6 weeks):

**Phase 1-2 (Weeks 1-2):**
- ✅ Omniparser package published
- ✅ epub2tts reorganized and validated
- ✅ All existing CLI features preserved
- ✅ All tests pass

**Phase 3 (Parallel):**
- ✅ WebGPU research complete
- ✅ Clear recommendation provided
- ✅ Decision made: Include/Post-MVP/Skip

**Phase 4-5 (Weeks 3-5):**
- ✅ Web backend functional
- ✅ Web frontend operational
- ✅ Upload → TTS → playback flow works
- ✅ Desktop experience polished
- ✅ Mobile experience accessible

**Phase 6 (Week 6):**
- ✅ Integration complete
- ✅ Documentation finished
- ✅ Ready for deployment

---

## Risk Assessment

### High Risks
1. **WebGPU Viability:** May not be feasible
   - *Mitigation:* Research first, server-side fallback

2. **Integration Complexity:** Many moving parts
   - *Mitigation:* Sequential validation, comprehensive testing

3. **Timeline Ambition:** 6 weeks is aggressive
   - *Mitigation:* Focus on MVP, defer nice-to-haves

### Medium Risks
1. **Omniparser Quality:** PDF/DOCX parsing challenging
   - *Mitigation:* Start with EPUB/PDF/TXT, add others iteratively

2. **Mobile Performance:** Unknown performance characteristics
   - *Mitigation:* Desktop-first, mobile as secondary goal

### Low Risks
1. **Abstract Interface:** Well-defined pattern
   - *Mitigation:* Clear spec, simple implementation

2. **CLI Preservation:** Existing code proven
   - *Mitigation:* Port don't rewrite, continuous testing

---

## Next Steps

### Immediate Actions:

1. **Review All Documents:**
   - Read WEB_READER_PROJECT_SPEC_v2.md
   - Read OMNIPARSER_PROJECT_SPEC.md
   - Read all three metaprompts
   - Understand architecture and approach

2. **Set Up Development Environment:**
   - Ensure UV is installed and working
   - Clone epub2tts repository
   - Create separate omniparser repository
   - Set up test fixtures

3. **Begin Phase 1:**
   - Launch Task agent with METAPROMPT_1
   - Monitor progress
   - Validate at each phase checkpoint
   - Proceed only after validation

4. **Parallel Research:**
   - Launch house-research agent with METAPROMPT_3
   - Review report when complete
   - Make WebGPU decision
   - Update web implementation plan if needed

### Weekly Cadence:

**Week 1:**
- Complete Omniparser extraction
- Begin repository reorganization

**Week 2:**
- Complete repository reorganization
- Begin web backend development
- Review WebGPU research

**Week 3:**
- Complete web backend
- Begin web frontend

**Week 4:**
- Continue web frontend
- Implement core Web Components

**Week 5:**
- Complete web frontend
- Begin integration testing

**Week 6:**
- Complete integration
- Polish and documentation
- MVP complete

---

## Documentation Status

### ✅ Complete
- [x] Updated Web Reader Project Spec (v2.0)
- [x] Omniparser Project Spec
- [x] Metaprompt #1: Omniparser Extraction
- [x] Metaprompt #2: Repository Reorganization
- [x] Metaprompt #3: WebGPU Research
- [x] Implementation Guide (this document)

### 📝 To Be Created During Implementation
- [ ] Omniparser README.md
- [ ] Omniparser API documentation
- [ ] epub2tts ARCHITECTURE.md
- [ ] epub2tts MIGRATION_GUIDE.md
- [ ] Web API documentation
- [ ] User guides (CLI + Web)
- [ ] Deployment documentation

---

## File Reference

All specification and metaprompt files are located in the epub2tts repository root:

```
/Users/autumn/Documents/Projects/epub2tts/
├── WEB_READER_PROJECT_SPEC.md          (original, 52 KB)
├── WEB_READER_PROJECT_SPEC_v2.md       (updated, 41 KB) ⭐
├── OMNIPARSER_PROJECT_SPEC.md          (36 KB) ⭐
├── METAPROMPT_1_OMNIPARSER_EXTRACTION.md (21 KB) ⭐
├── METAPROMPT_2_REPO_REORGANIZATION.md   (31 KB) ⭐
├── METAPROMPT_3_WEBGPU_RESEARCH.md       (25 KB) ⭐
└── IMPLEMENTATION_GUIDE.md               (this file) ⭐
```

**Key Files for Implementation (marked ⭐):**
1. Start with: WEB_READER_PROJECT_SPEC_v2.md (understand architecture)
2. Then: OMNIPARSER_PROJECT_SPEC.md (understand parsing layer)
3. Execute: METAPROMPT_1 → METAPROMPT_2 → Web development
4. Parallel: METAPROMPT_3 (research)

---

## Questions & Support

### Common Questions:

**Q: Should I start with web or Omniparser?**
A: Always start with Omniparser (Phase 1). It's a prerequisite for everything else.

**Q: Can I skip reorganization and go straight to web?**
A: No. Phase 2 (reorganization) must be complete before web development. The abstract interfaces are critical.

**Q: Should I wait for WebGPU research?**
A: No. Run WebGPU research in parallel. Start with server-side TTS in web implementation. Add WebGPU later if research is positive.

**Q: What if Omniparser tests fail?**
A: Do not proceed to Phase 2. Fix all issues in Phase 1 first. Each phase must be fully validated.

**Q: Can I modify the metaprompts?**
A: Yes, but understand the dependencies. Each phase builds on previous phases. Modifications should maintain the validation checkpoints.

### Getting Help:

If stuck:
1. Re-read the relevant spec document
2. Check the metaprompt for that phase
3. Review the Prerequisites and Validation sections
4. Ensure previous phases are truly complete

---

## Conclusion

All planning is complete. The project is well-specified with clear architecture, detailed implementation guides, and comprehensive validation checkpoints.

**The foundation is solid. Time to build.** 🚀

---

**Next Action:** Begin Phase 1 with METAPROMPT_1_OMNIPARSER_EXTRACTION.md

**Success Statement to Achieve:**
> "epub2tts web reader MVP is COMPLETE. CLI works. Web interface works. Kokoro TTS works. Desktop experience is polished. Mobile is accessible. All tests pass. Documentation is comprehensive. Ready for users."

---

**End of Implementation Guide**

*Last Updated: October 16, 2025*
*Status: Planning Complete - Ready for Implementation*
