# Project Instructions - Claude Code

> **Note**: This is the main orchestrator file. For detailed project-specific guides, see `agent.md`. For comprehensive workflow documentation, see `ClaudeUsage/README.md`

---

## Project Purpose
epub2tts is a production-ready EPUB to TTS converter that transforms EPUB files into optimized text and audio using multiple TTS engines (Kokoro, ElevenLabs, Hume AI) and local VLM for image descriptions.

## Tech Stack
- **Language**: Python 3.10+
- **Package Manager**: UV (modern Python package manager)
- **Key Libraries**: OmniParser (EPUB), spaCy (NLP), Kokoro/ElevenLabs/Hume (TTS), MLX (optimization)
- **Processing**: Modern NLP-based text processing with legacy regex fallback
- **VLM**: Local vision-language models (Gemma, LLaVA) for image descriptions

## Architecture Notes
- **Modular pipeline architecture**: EPUB → OmniParser → Modern Text Pipeline → TTS Engine
- **Multi-engine TTS support**: Kokoro (local), ElevenLabs (cloud), Hume AI (ultra-low latency)
- **Split-window terminal UI**: Real-time progress tracking with live stats
- **Production-ready**: Comprehensive logging, error handling, resume capability

---

## Essential Instructions (Always Follow)

### Python Commands
- **ALWAYS use `uv run` for Python commands** (e.g., `uv run python scripts/process_epub.py`)

### Context7 Integration
- **ALWAYS use Context7** when needing code generation, setup/configuration steps, or library/API documentation
- Automatically use Context7 MCP tools to resolve library IDs and get docs without explicit requests

### Project-Specific Instructions
- **For detailed project workflows and commands**: Read `agent.md`
- **For comprehensive best practices**: See `ClaudeUsage/README.md`

### Core Behavior
- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary for achieving your goal
- ALWAYS prefer editing existing files to creating new ones
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested

### Naming Conventions
- **Directories**: Use CamelCase (e.g., `VideoProcessor`, `AudioTools`, `DataAnalysis`)
- **Date-based paths**: Use skewer-case with YYYY-MM-DD (e.g., `logs-2025-01-15`, `backup-2025-12-31`)
- **No spaces or underscores** in directory names (except date-based paths)

### TODO Management
- **Always check `TODOS.md` first** when starting a task or session
- **Update immediately** when tasks are completed, added, or changed
- Keep the list current and manageable

### Git Workflow Essentials

**Branch Strategy:**
- Main branch: `main`
- Keep development work stable and tested before merging

**After completing major changes, you MUST:**
1. Check git status: `git status`
2. Review recent commits for style: `git log --oneline -5`
3. Stage changes: `git add .`
4. Commit with proper message format (see below)

**Commit Message Format:**
```
[Action] [Brief description]

- [Specific change 1 with technical detail]
- [Specific change 2 with technical detail]
- [Additional implementation details]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Action Verbs**: Add, Update, Fix, Refactor, Remove, Enhance

---

## When to Read Specific Guides

**Read the full guide when you encounter these situations:**

### Project-Specific Workflows
- **For epub2tts commands and workflows** → Read `agent.md`
- **For TTS engine specifics** → Read `agent.md`
- **For EPUB processing details** → Read `agent.md`

### Secrets & API Keys
- **When managing API keys or secrets** → Read `ClaudeUsage/secrets_management.md`
- **Before implementing secrets loading** → Read `ClaudeUsage/secrets_management.md`

### Package Management
- **When using UV package manager** → Read `ClaudeUsage/uv_usage.md`
- **Before creating pyproject.toml** → Read `ClaudeUsage/uv_usage.md`
- **When managing Python dependencies** → Read `ClaudeUsage/uv_usage.md`

### Version Control
- **Before making a git commit** → Read `ClaudeUsage/git_commit_guide.md`
- **For git workflow details** → Read `ClaudeUsage/git_workflow.md`

### Search & Research
- **When searching across 20+ files** → Read `ClaudeUsage/house_agents.md`
- **When finding patterns in codebase** → Read `ClaudeUsage/house_agents.md`
- **When locating TODOs/FIXMEs** → Read `ClaudeUsage/house_agents.md`

### Testing
- **Before writing tests** → Read `ClaudeUsage/testing_strategies.md`
- **When implementing test coverage** → Read `ClaudeUsage/testing_strategies.md`

### Code Quality
- **When refactoring code** → Read `ClaudeUsage/code_style_guide.md`
- **Before major code changes** → Read `ClaudeUsage/code_style_guide.md`

---

## Quick Reference

### Security Basics
- Store API keys in `secrets.json` (NEVER commit)
- `secrets.json` already in `.gitignore`
- Template provided as `secrets_template.json`
- Environment variables as fallbacks supported

### House Agents Quick Trigger
**When searching 20+ files**, use house-research for:
- Finding patterns across codebase
- Searching TODO/FIXME comments
- Locating API endpoints or functions
- Documentation searches

---

## Code Style Guidelines

### Function & Variable Naming
- Use meaningful, descriptive names
- Keep functions small and focused on single responsibilities
- Add docstrings to functions and classes

### Error Handling
- Use try/except blocks gracefully
- Provide helpful error messages
- Never let errors fail silently

### File Organization
- Group related functionality into modules
- Use consistent import ordering:
  1. Standard library
  2. Third-party packages
  3. Local imports
- Keep configuration separate from logic

---

## Communication Style
- Be concise but thorough
- Explain reasoning for significant decisions
- Ask for clarification when requirements are ambiguous
- Proactively suggest improvements when appropriate

---

## Complete Guide Index
- **Project-specific documentation**: See `agent.md`
- **General workflow guides**: See `ClaudeUsage/README.md`

---

*Last updated: 2025-10-29*
*Model: Claude Sonnet 4.5*