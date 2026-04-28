---
name: FastAPI Task Manager
domain: code
version: "1.0"
status: draft
created: "2026-04-28T10:00:00+00:00"
tags: [fastapi, sqlite, pydantic, pytest]
agents: [slopcontrol]
---

# Requirements
- REST API with full CRUD for tasks
- SQLite database with SQLAlchemy ORM
- Pydantic models for request/response validation
- JWT authentication for protected endpoints
- pytest with 80% line coverage
- ruff for linting and formatting
- mypy for type checking

# Design Decisions

## 1. Framework Choice
- **Decision:** FastAPI over Flask/Django
- **Rationale:** Native async support, automatic OpenAPI docs, Pydantic integration
- **Consequence:** Slightly steeper learning curve for new contributors

## 2. Database Layer
- **Decision:** SQLite for simplicity, SQLAlchemy ORM for portability
- **Rationale:** Zero setup, single file, easy to migrate to PostgreSQL later
- **Parameters:**
  - Connection string: `sqlite:///./tasks.db`
  - Async engine: `create_async_engine`

## 3. Authentication
- **Decision:** JWT tokens via python-jose
- **Rationale:** Stateless, works well with FastAPI dependency injection
- **Parameters:**
  - Algorithm: HS256
  - Token expiry: 30 minutes
  - Refresh token: 7 days

## 4. Project Structure
- **Decision:** Standard package layout with `src/` and `tests/`
- **Rationale:** Aligns with Python packaging best practices

# Implementation Steps
1. Initialize project structure and dependencies
2. Define Pydantic models (Task, User, Token)
3. Implement database models and migrations
4. Build CRUD endpoints for tasks
5. Add JWT authentication layer
6. Write comprehensive pytest suite
7. Configure ruff and mypy pre-commit hooks
8. Generate OpenAPI documentation

# Verification Log
| Version | Check | Result | Notes |
|---|---|---|---|
| 1.0 | pytest | pending | Target 80% coverage |
| 1.0 | mypy | pending | Strict mode |
| 1.0 | ruff | pending | Format + lint |

# Appendices

## Appendix A: API Contract
```
GET    /tasks          List all tasks
POST   /tasks          Create task
GET    /tasks/{id}     Get task
PUT    /tasks/{id}     Update task
DELETE /tasks/{id}     Delete task
POST   /auth/login     Login (returns JWT)
POST   /auth/register  Register new user
```

## Appendix B: Database Schema
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    done BOOLEAN DEFAULT FALSE,
    owner_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
