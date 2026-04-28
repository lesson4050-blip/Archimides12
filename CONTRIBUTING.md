# Contributing to Archimedes 12

Thank you for contributing! This guide ensures consistent quality across the codebase.

## Development Setup

```bash
# Clone and install
git clone <repo-url> && cd Cosmo
pip install -r requirements.txt
pip install pre-commit ruff pytest pytest-asyncio

# Install pre-commit hooks
pre-commit install

# Create local .env (auth disabled for dev)
cp .env.example .env
```

## Code Standards

### Python
- **Style**: ruff (configured in `pyproject.toml`)
- **Type hints**: Required on all public functions
- **Async**: All tool `.execute()` methods must be `async`
- **Logging**: Use `logging.getLogger(__name__)`, never `print()`
- **Exceptions**: Never use bare `except:` — always specify the exception type

### Testing
- All new modules must have a corresponding `tests/test_<module>.py`
- Use `pytest.mark.asyncio` for async tests
- Mock external APIs — never make real HTTP calls in tests
- Target: **80%+ coverage** (enforced in CI)

```bash
# Run tests
python -m pytest tests/ -v --tb=short

# Run with coverage
python -m pytest tests/ --cov=backend --cov-report=term-missing
```

### Security
- `AUTH_ENABLED=True` in production (default)
- All shell commands are checked against `BLOCKED_SHELL_PATTERNS`
- Session IDs must match: `^[a-zA-Z0-9_\-]{1,128}$`
- File paths are validated against traversal attacks
- Rate limiting: 60 req/min per IP

## Architecture

```
backend/
├── agent/           # Core agent logic (OmegaCodeAct, HydraSwarm, MCTS)
├── api/             # FastAPI routes
├── auth/            # JWT authentication
├── memory/          # KnowledgeGraph, MemoryBank, ContextManager
├── middleware/       # Security (rate limit, headers)
├── models/          # Model router (Ollama → Groq → Gemini)
├── sandbox/         # Docker container management
├── tools/           # Tool implementations (shell, file, AST, etc.)
└── utils/           # JSON repair, observability, tool schemas
```

## Pull Request Checklist

- [ ] Tests pass: `python -m pytest tests/ -v`
- [ ] Linter clean: `ruff check .`
- [ ] No new bare `except:` blocks
- [ ] New features have tests
- [ ] Docstrings on public functions
- [ ] No hardcoded secrets or API keys
