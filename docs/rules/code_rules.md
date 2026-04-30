# Coding Rules

## SQLAlchemy & Database

### Use SQLAlchemy 2.0 style exclusively
Do not use `.query()` or old-style ORM patterns. Use `select()`, `.where()`, `.scalars()`.

### Use `&` / `|` operators, not `and_()` / `or_()`
Boolean composition in queries goes through bitwise operators on column expressions.

### Explicit `nullable=False` on Boolean columns
Always set `nullable=False` on Boolean model columns. Don't rely on defaults to imply non-nullability.

### Use `Mapped[]` annotations with `mapped_column()`
Use modern SQLAlchemy declarative typing. For relationships, properly type `Mapped["Model"]` (or `Mapped[list["Model"]]`) so you don't need explicit `uselist=False`.

### Use `exists()` for boolean queries
Don't fetch full objects when you only need a boolean result. Use `exists()` subqueries.

### Migrations only manage seed data you control
A migration must never delete or rewrite rows that the application or its users could have created. Limit data manipulation to seed/reference data the migration itself owns.

### Let PostgreSQL manage auto-incrementing sequences
Don't manually set or reset sequence values in migrations.

### Don't hardcode data in migrations
Constants and seed data should be loaded from external files (CSV, JSON, etc.) programmatically, not pasted into the migration script.

---

## Module Architecture

### Never reach into another module's CRUD or models directly
Always go through that module's service or crud layer. This applies to production code AND tests. If module A needs data owned by module B, B must expose a function for it.

### Router = validation, CRUD = database logic
Routers handle HTTP-level validation and error mapping. Database queries, commits, and relationship assignments live in `crud.py`. Filtering and validation should happen before reaching processing functions, not inside them.

### Domain logic lives in domain modules
Queries about a domain entity belong in that entity's `service.py` + `crud.py`, not scattered across other modules.

### No one-off scripts
Data pipelines, conversion logic, and admin operations must be proper functions in the codebase (e.g. seeding functions or CLI commands), not standalone scripts.

### Cached properties for derived values
When a value is computed from instance data, expose it as a `@cached_property` on the class rather than recomputing it at each call site.

---

## Data & Config

### Don't hardcode data — read programmatically
Field mappings, reference lists, and any non-trivial constants should come from DB, config files, or pydantic models — not be embedded as Python literals scattered through the code.

### Abort on unexpected data
If you encounter data that doesn't match expectations (unknown enum value, unmapped key, malformed input), fail loudly and stop. Don't silently skip or default.

### Use pydantic model fields as the single source of truth
Don't maintain parallel lists of column or field names. Derive them from the pydantic model.

### Constants are module-level declarations, not runtime assignments
Don't build constant values inside `init` or factory functions. Declare them at module scope.

---

## Code Style

### No "step" comments or comments that restate code
Strip `# Step 1:`, `# Step 2:`, and any comment that simply paraphrases the next line. Comments are only for non-obvious *why*.

### Log enough fields to uniquely identify a record
Don't log a single id-like field (e.g. `source_url`) if it isn't actually unique. Log the full composite identifier so the log entry is independently actionable.

### Don't log warnings or errors for expected behavior
If a condition is expected and handled, it's not a warning. Use the appropriate level (info/debug) or don't log it.

### Boolean parameters: use `bool`, not `Optional[bool]`
A boolean flag with three states is a code smell. Use a concrete `bool` with a descriptive name (`need_to_verify_db_existence` rather than `pc_exists_in_db`).

### Don't use `.get()` when the key must exist
`.get()` implies the key may be absent. If the key is required, use `[]` so missing keys fail loudly.

---

## Testing

### Test fixtures should be specific and deterministic
Use named lookups (`get_by_abbrev("UT")`), not positional indexing into query results. Tests must be reproducible across runs.

### Session-scoped fixtures for reference data
Immutable reference data fixtures should be session-scoped to avoid redundant DB calls.

### Test setup uses the service/crud layer
Don't manipulate ORM objects directly in tests. Use the same service/crud functions the application uses.

### Use a simple generator pattern for `get_db()`
Use `for session in get_db()` rather than `contextmanager` + `suppress` workarounds.

---

## Git & PR Hygiene

### Delete temporary or working files before merging
Comparison documents, scratch mappings, and other working artifacts must be removed before the PR is ready.

### Don't commit review documents or plan files
Code review notes, PR review markdown, plan files — keep them out of the repo.

### Split unrelated changes into separate PRs
Logically independent changes belong in their own PRs, even if they touch the same files.
