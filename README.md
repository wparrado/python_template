# Python FastAPI Hexagonal Architecture Template

A production-ready and academically correct project template implementing
**Clean Hexagonal Architecture (Ports & Adapters)** with FastAPI, enforced
at multiple levels: architectural tests, module boundary checks, import contracts,
strict typing, and quality gates at commit and push time.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  presentation   (primary adapters — FastAPI routers)         │
│  • HTTP schemas (Pydantic)       • Middlewares               │
│  • Error handlers                • Schema ↔ DTO mappers      │
│  ↓ depends on application only                               │
├──────────────────────────────────────────────────────────────┤
│  infrastructure  (secondary adapters — implements ports)     │
│  • Persistence adapters          • OIDC auth adapter         │
│  • OpenTelemetry observability   • Domain event publisher    │
│  ↓ depends on domain ports + application DTOs               │
├──────────────────────────────────────────────────────────────┤
│  application  (use cases — CQRS handlers)                    │
│  • Commands + Queries            • Command/Query Handlers    │
│  • Application DTOs (Pydantic)   • Domain ↔ DTO mappers      │
│  • Result[T, E] error handling                               │
│  ↓ depends on domain only                                    │
├──────────────────────────────────────────────────────────────┤
│  domain  ◆ PURE PYTHON — zero external dependencies         │
│  • Aggregate roots + Entities    • Value objects             │
│  • Primary ports (inbound)       • Secondary ports (outbound)│
│  • Domain events                 • Domain exceptions         │
└──────────────────────────────────────────────────────────────┘
```

### Dependency Rule (enforced by 3 tools)
```
presentation  →  application  →  domain  (pure Python)
infrastructure  →  domain ports  (implements outbound ports)
```

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker + docker-compose (optional, for containerized runs)

---

## Setup

```bash
# Install all dependencies (runtime + dev)
uv sync

# Copy environment config
cp .env.example .env

# Install git hooks
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

---

## Running

```bash
# Development server (Granian ASGI)
uv run granian --interface asgi app.main:app --host 0.0.0.0 --port 8000 --reload

# Or via Docker
docker-compose up --build
```

API docs: http://localhost:8000/docs

---

## Testing

```bash
# All tests
uv run pytest

# Unit tests only (fast, no I/O)
uv run pytest tests/unit/ -v

# Integration (adapter contract) tests
uv run pytest tests/integration/ -v

# Architectural dependency tests
uv run pytest tests/architecture/ -v
```

---

## Architecture Enforcement

Three independent tools guard the dependency rules:

```bash
# 1. dtach — module boundary declarations (tach.toml)
uv run tach check

# 2. import-linter — contract-based import checks (.importlinter)
uv run lint-imports

# 3. pytest-archon — runtime import graph assertions
uv run pytest tests/architecture/ -v
```

---

## Quality Gates

```bash
# Type checking (mypy strict)
uv run mypy src/

# Linting (pylint)
uv run pylint src/app

# Formatting (ruff)
uv run ruff format src/ tests/
uv run ruff check src/ tests/
```

All of the above run automatically via pre-commit on every `git commit` and `git push`.

---

## Configuration

All configuration is environment-variable driven via Pydantic Settings.

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `app` | Application name |
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Log level |
| `OIDC_ISSUER` | _(empty)_ | OIDC provider URL (empty = auth disabled) |
| `OIDC_AUDIENCE` | _(empty)_ | Expected JWT audience |
| `OTEL_ENABLED` | `false` | Enable OpenTelemetry export |
| `OTEL_SERVICE_NAME` | `app` | Service name in traces/metrics |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP backend endpoint |

### Connecting an OIDC Provider

Set `OIDC_ISSUER` to any standards-compliant OIDC provider:

```bash
# Keycloak
OIDC_ISSUER=https://keycloak.example.com/realms/myrealm
OIDC_AUDIENCE=my-client

# Auth0
OIDC_ISSUER=https://dev-xyz.us.auth0.com/
OIDC_AUDIENCE=https://api.example.com

# AWS Cognito
OIDC_ISSUER=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxx
OIDC_AUDIENCE=my-app-client-id
```

### Connecting an Observability Backend

Set `OTEL_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT`:

```bash
# Jaeger (local)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Grafana Tempo
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317

# Or use docker-compose with the otel-collector (see otel-config.yaml)
```

---

## Adding a New Use Case — Step by Step

### 1. Domain: add to the aggregate (if needed)
```python
# src/app/domain/model/example/item.py
def deactivate(self) -> None:
    self._validate_can_deactivate()
    self._record_event(ItemDeactivated(aggregate_id=self.id))
```

### 2. Application: add command + handler
```python
# src/app/application/commands/item_commands.py
@dataclass(frozen=True)
class DeactivateItemCommand:
    item_id: uuid.UUID

# src/app/application/handlers/command_handlers.py
class DeactivateItemHandler:
    async def handle(self, command: DeactivateItemCommand) -> Result[ItemOutputDTO, DomainError]:
        ...
```

### 3. Presentation: add route
```python
# src/app/presentation/api/v1/routers/items.py
@router.post("/{item_id}/deactivate", response_model=ItemResponse)
async def deactivate_item(item_id: uuid.UUID, ...) -> ItemResponse:
    ...
```

### 4. Container: wire the new handler
```python
# src/app/container.py
def deactivate_item_handler(self) -> DeactivateItemHandler:
    return DeactivateItemHandler(repository=self._item_repository, ...)
```

### 5. Tests: add unit + architecture tests
The architecture tests already guard the new code automatically.

---

## Swapping the Persistence Adapter

The `Item` aggregate and `IItemRepository` port **never change**.

1. Create `infrastructure/persistence/sqlalchemy/item_repository.py`
2. Implement `IItemRepository`
3. Update `Container.create_item_handler()` to inject the new adapter
4. Add the new adapter to the parametrized fixture in `tests/integration/infrastructure/test_item_repository_contract.py`

See `src/app/infrastructure/persistence/README.md` for a detailed guide.

---

## Project Structure

```
src/app/
├── domain/              ◆ Pure Python — ZERO external deps
│   ├── model/           Aggregate roots, entities, value objects
│   ├── ports/           Inbound + outbound abstract interfaces
│   ├── events/          Domain event base
│   └── exceptions/      Domain error hierarchy
├── application/         CQRS handlers, DTOs, mappers, Result type
├── infrastructure/      Adapters: persistence, auth, observability, events
└── presentation/        FastAPI routers, schemas, middlewares, error handlers
```
