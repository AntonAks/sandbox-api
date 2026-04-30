# sandbox-api

Baseline API for an AI workshop on diagnosing performance problems with Claude Code. The full project specification lives in `docs/spec.md` — read it before suggesting or implementing anything.

## Stack (fixed by spec)

Python 3.12, FastAPI, SQLAlchemy 2.0 async + asyncpg, PostgreSQL 16, Alembic, structlog, pydantic-settings. Dependency management via `uv` (NOT poetry). Docker + docker-compose for local and prod. GitHub Actions for CI/CD, ghcr.io for images, OpenTofu/Terraform on Hetzner for infra. `justfile` for command shortcuts.

## Coding rules

@docs/rules/code_rules.md

## Workflow rules (from `docs/spec.md`, "Workflow на цьому етапі")

- Clarifying questions go in **ONE** message, before any code is written. Don't trickle them out.
- Propose a plan (list of files to be created, in what order) and wait for an explicit "ок, починай" before touching code.
- Implement in stages: local dev (compose + app + tests) → CI → Terraform + deploy. After each stage, give a short status update.
- The user runs `tofu apply` / `terraform apply` **manually** — never execute these, even in passing.
- Test CI changes via a **draft PR**. Never push directly to `main`.

## Hard constraints from spec

- Baseline must stay **vanilla and unoptimized** — performance bugs will be added intentionally in the workshop content phase. Do not pre-optimize.
- The "Що НЕ робити на цьому етапі" section in `docs/spec.md` is a hard list, not a soft preference. No Redis, no Prometheus, no auth, no application-level rate limiting, no pre-commit hooks, no domain logic beyond skeleton — at this phase.
- Do not add features or refinements outside the spec without asking first.

## Project layout

- `docs/spec.md` — load-bearing project specification.
- `docs/rules/` — coding rules (imported above).
- `docs/workshop/` — educational notes for workshop preparation; not user-facing project docs.
- `.claude/` — Claude Code configuration (settings, hooks, custom skills).
