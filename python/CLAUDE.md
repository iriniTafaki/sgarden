# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SGarden is an Inventory Management REST API built with FastAPI, Motor (async MongoDB), and JWT authentication. There is a parallel Java Spring Boot implementation under `../java/` that exposes the same API surface.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment (template at ../.env.sample)
cp ../.env.sample ../.env

# Start the server (default port 4000)
uvicorn main:app --host 0.0.0.0 --port 4000 --reload
# or
python main.py
```

Key environment variables (all optional, defaults are shown):
```
DATABASE_URL=mongodb://localhost:27017/sgarden
PORT=4000
SERVER_SECRET=sgarden-secret-key
JWT_EXPIRATION_HOURS=24
```

MongoDB must be running before startup. On first boot, the app creates unique indexes on `username` and `email` and seeds two test users (`admin`/`admin123`, `user`/`user1234`) and 15 sample products.

API docs are auto-generated at `http://localhost:4000/docs` (Swagger) and `/redoc`.

## Architecture

The app uses a three-layer structure: **routes → database → models**.

- `main.py` — FastAPI app, CORS middleware, lifespan (indexes + seed), router registration
- `config.py` — Pydantic `BaseSettings`; reads `.env` from the parent directory
- `database.py` — Async Motor client; exposes `users_collection` and `products_collection`
- `security/jwt_handler.py` — JWT creation/verification; `get_current_user()` is the FastAPI dependency for protected routes
- `routes/` — Thin handlers; business logic lives directly in route functions (the `services/` layer is empty)
- `models/` — Pydantic v2 models for validation and serialization
- `seed.py` — Standalone async seeding script, also called from `main.py` lifespan

### Route groups

| Prefix | File | Notes |
|---|---|---|
| `/api/auth` | `routes/auth.py` | Register, login — returns JWT |
| `/api/products` | `routes/products.py` | Full CRUD; write endpoints require `Bearer` token |
| `/api/users` | `routes/users.py` | Profile, search, admin actions |
| `/api/health` | `main.py` | Liveness check |

## Intentional Code Flaws

This codebase is a **teaching/demo project** and contains deliberate code quality issues for review and refactoring exercises:

- **Duplicate symbols** — `V2`-suffixed model classes, `register_user` vs `register`, `format_product` vs `product_to_response`, `user_to_response` vs `user_to_response_safe`, `get_current_user` vs `get_current_user_deprecated`
- **Unused variables** — `APP_NAME`, `DEBUG_MODE`, `unused_config`, `auth_version`, `service_name`, `API_VERSION`, `DEPRECATED_FIELD`, `_temp_cache`, `token_cache`, `search_id`
- **Intentional security vulnerabilities** present in `routes/users.py` (command injection at `/api/users/system/info`, path traversal at `/api/users/reports/download`, NoSQL injection in `/api/users/search`, MD5 usage at `/api/users/hash`)

When asked to review or fix this code, treat these as in-scope targets rather than pre-existing issues to ignore.

## No Test or Lint Tooling

There is no pytest setup, no linting configuration (flake8/ruff/black), and no CI pipeline. All verification is manual via the Swagger UI or `curl`.
