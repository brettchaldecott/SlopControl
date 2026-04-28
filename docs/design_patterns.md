# Code Design Patterns

This guide covers common software design patterns and how to implement them with SlopControl.

## 1. REST API with CRUD

A standard REST API with Create, Read, Update, Delete operations.

### Description
- Resource-based routing
- Pydantic models for request/response validation
- SQLite database via SQLAlchemy or similar
- Comprehensive pytest coverage

### Plan Request
```
Build a FastAPI REST API for managing tasks with SQLite, Pydantic models,
and full CRUD endpoints. Include pytest tests with 80% coverage.
```

### Implementation Pattern
```python
# 1. Define Pydantic models
class Task(BaseModel):
    id: int
    title: str
    done: bool = False

# 2. Create database layer
# 3. Implement CRUD endpoints
# 4. Write tests
```

## 2. CLI Tool

A command-line tool built with Typer.

### Description
- Subcommands for different operations
- Rich terminal output
- Configuration file support
- Type hints throughout

### Plan Request
```
Build a CLI tool with Typer that manages a task list. Support adding,
listing, completing, and deleting tasks. Store in a JSON file.
```

## 3. Python Library

A reusable library with a clean public API.

### Description
- `__init__.py` exports the public API
- Internal modules prefixed with `_`
- Comprehensive docstrings
- Full type hints
- pytest + mypy + ruff verification

### Plan Request
```
Build a Python library for parsing and validating email addresses.
Include a clean public API, comprehensive tests, and type hints.
```

## 4. Background Worker

A worker that processes tasks from a queue.

### Description
- Async/await pattern
- Graceful shutdown handling
- Retry logic with exponential backoff
- Structured logging

### Plan Request
```
Build an async background worker that processes jobs from a SQLite queue.
Include retry logic, logging, and graceful shutdown.
```

## 5. Plugin Architecture

A system that loads plugins dynamically.

### Description
- Entry points or filesystem discovery
- Plugin registration API
- Error isolation (one bad plugin doesn't crash the system)
- Examples included

### Plan Request
```
Build a plugin-based tool that discovers and loads Python modules
from a plugins/ directory. Include a sample plugin and tests.
```

## 6. Event-Driven System

A system that reacts to events.

### Description
- Event bus / pub-sub pattern
- Typed events
- Async handlers
- Testable with mock events

### Plan Request
```
Build an event-driven system with an in-memory event bus.
Support typed events, async handlers, and subscription management.
```

## 7. Data Pipeline

A pipeline that transforms data through multiple stages.

### Description
- Stage-based architecture
- Input/output contracts per stage
- Error handling and fallback stages
- Progress reporting

### Plan Request
```
Build a data pipeline that reads CSV, validates rows, transforms data,
and writes to SQLite. Include error handling and progress reporting.
```

## 8. Authentication Layer

Add authentication to an existing API.

### Description
- JWT or OAuth2
- Middleware for protected routes
- Token refresh
- Test users for testing

### Plan Request
```
Add JWT authentication to the existing FastAPI app. Include login,
register, and protected endpoints. Write tests.
```

## 9. Caching Layer

Add caching to improve performance.

### Description
- In-memory or Redis caching
- Cache invalidation strategy
- Cache-aside or write-through patterns
- Metrics on cache hit/miss

### Plan Request
```
Add a caching layer to the existing API using an in-memory LRU cache.
Include cache invalidation and hit/miss metrics.
```

## 10. Webhook Receiver

A service that receives and processes webhooks.

### Description
- Signature verification
- Idempotency key handling
- Async processing
- Retry queue for failures

### Plan Request
```
Build a webhook receiver with signature verification and idempotency.
Queue failed webhooks for retry. Include tests.
```

## Development Best Practices

### 1. Type Hints
Use `typing` everywhere. Run mypy to catch errors.

### 2. Testing
- Unit tests for individual functions
- Integration tests for endpoints
- Use pytest fixtures for setup

### 3. Error Handling
- Custom exceptions for domain errors
- Graceful degradation
- Structured logging

### 4. Verification
Run verifiers often:
```bash
slopcontrol verify --domain code
```

## Common Tooling

| Tool | Purpose |
|------|---------|
| pytest | Unit and integration tests |
| mypy | Static type checking |
| ruff | Linting and formatting |
| pytest-cov | Coverage reporting |
| pre-commit | Pre-commit hooks |
