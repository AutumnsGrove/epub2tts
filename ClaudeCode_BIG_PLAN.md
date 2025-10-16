 OmniParser Extraction & epub2tts Migration Plan                                  │
     │                                                                                  │
     │ Phase 1: RESEARCH (Complete ALL research before development)                     │
     │                                                                                  │
     │ Subagent 1.1: Requirements Analysis                                              │
     │                                                                                  │
     │ Task: Analyze ebooklib_processor.py comprehensively                              │
     │ - Extract all methods, classes, and functionality                                │
     │ - Document dependencies and imports                                              │
     │ - Identify integration points with epub2tts                                      │
     │ - Map data structures and interfaces                                             │
     │ - Output: research/ebooklib_analysis.md                                          │
     │                                                                                  │
     │ Subagent 1.2: Test Strategy Analysis                                             │
     │                                                                                  │
     │ Task: Analyze existing test suite                                                │
     │ - Review test files and fixtures                                                 │
     │ - Document expected behaviors                                                    │
     │ - Identify test gaps                                                             │
     │ - Plan test fixtures for OmniParser                                              │
     │ - Output: research/test_strategy.md                                              │
     │                                                                                  │
     │ Subagent 1.3: Dependency Mapping                                                 │
     │                                                                                  │
     │ Task: Map all dependencies for OmniParser                                        │
     │ - Extract Python package requirements                                            │
     │ - Identify version constraints                                                   │
     │ - Document epub2tts → OmniParser migration path                                  │
     │ - Plan import restructuring                                                      │
     │ - Output: research/dependency_map.md                                             │
     │                                                                                  │
     │ Subagent 1.4: Architecture Planning                                              │
     │                                                                                  │
     │ Task: Design OmniParser architecture                                             │
     │ - Plan module structure per METAPROMPT_1                                         │
     │ - Design BaseParser interface                                                    │
     │ - Plan data model transformations                                                │
     │ - Define migration strategy for epub2tts                                         │
     │ - Output: research/architecture_plan.md                                          │
     │                                                                                  │
     │ ---                                                                              │
     │ Phase 2: DEVELOPMENT (After research complete)                                   │
     │                                                                                  │
     │ Stage 2.1: OmniParser Foundation (Phases 1-5)                                    │
     │                                                                                  │
     │ Subagent 2.1: Repository setup, data models, exceptions, utilities               │
     │ - Create project structure                                                       │
     │ - Implement all data models (Document, Chapter, Metadata, etc.)                  │
     │ - Implement exception classes                                                    │
     │ - Implement utility functions (format detection, encoding)                       │
     │ - Deliverable: Functional OmniParser skeleton with tests                         │
     │                                                                                  │
     │ Stage 2.2: EPUB Parser Port (Phase 6)                                            │
     │                                                                                  │
     │ Subagent 2.2: Port ebooklib_processor.py to OmniParser                           │
     │ - Adapt 964-line processor to BaseParser interface                               │
     │ - Implement EPUB-specific functionality                                          │
     │ - Handle TOC, images, metadata extraction                                        │
     │ - Adapt TextCleaner integration                                                  │
     │ - Deliverable: Working EPUBParser with unit tests                                │
     │                                                                                  │
     │ Stage 2.3: Additional Parsers (Phases 7-10)                                      │
     │                                                                                  │
     │ Parallel Subagents 2.3a-d: Implement PDF, DOCX, HTML, Markdown/Text parsers      │
     │ - Each subagent handles one parser implementation                                │
     │ - Follow BaseParser interface                                                    │
     │ - Include basic test coverage                                                    │
     │ - Deliverable: 5 working parsers (EPUB + 4 others)                               │
     │                                                                                  │
     │ Stage 2.4: Post-Processing & Integration (Phases 11-13)                          │
     │                                                                                  │
     │ Subagent 2.4: Complete OmniParser package                                        │
     │ - Implement processors (chapter detection, metadata extraction, text cleaning)   │
     │ - Implement main parse_document() function                                       │
     │ - Configure package exports                                                      │
     │ - Create documentation and examples                                              │
     │ - Deliverable: Complete OmniParser package ready for testing                     │
     │                                                                                  │
     │ ---                                                                              │
     │ Phase 3: TESTING (After development complete)                                    │
     │                                                                                  │
     │ Stage 3.1: OmniParser Testing                                                    │
     │                                                                                  │
     │ Subagent 3.1: Run OmniParser test suite                                          │
     │ - Execute all unit tests                                                         │
     │ - Execute integration tests                                                      │
     │ - Generate coverage report (target: >80%)                                        │
     │ - Document any issues                                                            │
     │ - Deliverable: Validated OmniParser package                                      │
     │                                                                                  │
     │ Stage 3.2: Package Building                                                      │
     │                                                                                  │
     │ Bash Subagent 3.2: Build and validate package                                    │
     │ - Run uv build                                                                   │
     │ - Test local installation                                                        │
     │ - Validate imports work                                                          │
     │ - Run example scripts                                                            │
     │ - Deliverable: Installable OmniParser package                                    │
     │                                                                                  │
     │ ---                                                                              │
     │ Phase 4: EPUB2TTS MIGRATION (After OmniParser validated)                         │
     │                                                                                  │
     │ Stage 4.1: Migration Planning                                                    │
     │                                                                                  │
     │ Subagent 4.1: Plan epub2tts restructuring per METAPROMPT_2                       │
     │ - Map all file moves                                                             │
     │ - Identify import changes                                                        │
     │ - Plan dependency updates                                                        │
     │ - Document breaking changes                                                      │
     │ - Deliverable: Migration blueprint                                               │
     │                                                                                  │
     │ Stage 4.2: Repository Restructuring                                              │
     │                                                                                  │
     │ Subagent 4.2: Reorganize epub2tts structure                                      │
     │ - Create new directory structure (/core/, /audio-processing/, /web/, /cli/)      │
     │ - Move files to new locations                                                    │
     │ - Update all imports                                                             │
     │ - Add OmniParser dependency                                                      │
     │ - Remove old EPUB processing code                                                │
     │ - Deliverable: Restructured epub2tts                                             │
     │                                                                                  │
     │ Stage 4.3: Integration Testing                                                   │
     │                                                                                  │
     │ Subagent 4.3: Validate epub2tts functionality                                    │
     │ - Run existing test suite                                                        │
     │ - Verify CLI still works                                                         │
     │ - Test end-to-end EPUB processing                                                │
     │ - Document any regressions                                                       │
     │ - Deliverable: Working epub2tts with OmniParser                                  │
     │                                                                                  │
     │ ---                                                                              │
     │ Success Criteria                                                                 │
     │                                                                                  │
     │ OmniParser Package:                                                              │
     │ - ✅ All 16 phases of METAPROMPT_1 complete                                       │
     │ - ✅ Test coverage >80%                                                           │
     │ - ✅ Package builds successfully                                                  │
     │ - ✅ Can install via uv add omniparser                                            │
     │                                                                                  │
     │ epub2tts Migration:                                                              │
     │ - ✅ Repository reorganized per METAPROMPT_2                                      │
     │ - ✅ All existing tests pass                                                      │
     │ - ✅ CLI functionality preserved                                                  │
     │ - ✅ Uses OmniParser for document parsing                                         │
     │                                                                                  │
     │ ---                                                                              │
     │ Estimated Timeline                                                               │
     │                                                                                  │
     │ - Phase 1 (Research): 4 subagents (~1-2 hours)                                   │
     │ - Phase 2 (OmniParser Development): 6 subagents (~4-6 hours)                     │
     │ - Phase 3 (Testing): 2 subagents (~1 hour)                                       │
     │ - Phase 4 (Migration): 3 subagents (~2-3 hours)                                  │
     │                                                                                  │
     │ Total: ~15 subagents, 8-12 hours of work                                         │
     │                                                                                  │
     │ ---                                                                              │
     │ Notes                                                                            │
     │                                                                                  │
     │ 1. Test Fixtures: sample_epubs/ is empty - will need to create/obtain test EPUBs │
     │ 2. Bash Subagents: Will be used for build/test commands to reduce context        │
     │ 3. Parallel Execution: Parsers 2.3a-d can run in parallel for efficiency         │
     │ 4. Strict Ordering: Cannot proceed to next phase until current phase is complete