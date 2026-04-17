# Architecture Reference — Hexagonal Architecture Blueprint

> **Purpose**: This document is a technology-agnostic, high-level description of the
> architecture, patterns, practices, and guards implemented in this project. It is
> intended to be used as a reference prompt for an AI system to replicate this
> structure in any programming language or ecosystem.

---

## 1. Architectural Style — Hexagonal Architecture (Ports & Adapters)

The project follows **Hexagonal Architecture**, also known as the **Ports & Adapters**
pattern, introduced by Alistair Cockburn. The central idea is that the application core
(domain + use cases) is completely isolated from external concerns (HTTP, databases,
message brokers, authentication providers, etc.) through abstract interfaces called
**ports**, implemented by **adapters**.

### 1.1 The Dependency Rule

Dependencies flow strictly **inward**:

```
presentation  →  application  →  domain
infrastructure  →  domain (implements outbound ports)
infrastructure  →  application (implements application-level ports)
```

- The **domain** has zero outward dependencies. It knows nothing about frameworks,
  databases, HTTP, or even the application layer.
- The **application** layer depends only on the domain. It does not import from
  infrastructure or presentation.
- The **infrastructure** layer implements ports defined by the domain and application.
  It imports from both but is never imported by them.
- The **presentation** layer imports only from the application layer, never from the
  domain model or infrastructure directly.

### 1.2 The Four Layers

```
┌──────────────────────────────────────────────────────────────┐
│  PRESENTATION  (primary adapters — driving side)             │
│  Translates external input (HTTP, CLI, gRPC) into           │
│  application port calls. Returns application DTOs.           │
│  Maps domain errors to protocol-specific responses.          │
├──────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE  (secondary adapters — driven side)          │
│  Implements outbound ports: persistence, messaging,          │
│  authentication, observability, resilience.                  │
├──────────────────────────────────────────────────────────────┤
│  APPLICATION  (use cases — orchestration)                    │
│  CQRS handlers, application services, DTOs, mappers.        │
│  Defines inbound ports (what it offers) and uses outbound   │
│  ports (what it needs from infrastructure).                  │
├──────────────────────────────────────────────────────────────┤
│  DOMAIN  ◆ PURE — zero external dependencies                │
│  Aggregates, entities, value objects, domain events,        │
│  domain exceptions, outbound ports, specifications.         │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Domain Layer Patterns

The domain layer is the most protected layer. It contains only the language of the
business and must compile/run with no external library dependencies.

### 2.1 Entity

An **Entity** is an object defined by its identity, not its attributes. Two entities
with the same identity are the same object regardless of their current state.

- Has a stable, unique identifier (typically a UUID assigned at creation).
- Carries audit fields: creation timestamp, last-update timestamp.
- Supports soft deletion via a boolean flag (avoids hard deletes at the domain level).
- Equality is based solely on identity.
- Hash is derived from identity to allow use in collections.
- Provides an internal method to advance the update timestamp, accepting an injected
  clock abstraction so time is always deterministic in tests.

### 2.2 Value Object

A **Value Object** is an immutable object defined entirely by its attributes. Two value
objects with the same attributes are interchangeable.

- Immutable after construction — all fields are set once and never changed.
- Self-validating: invariants are enforced in the constructor. An invalid value object
  cannot exist.
- Compared by value, not identity.
- Wraps primitives (strings, numbers, UUIDs) in typed, named wrappers to prevent
  primitive obsession and make the domain model expressive.
- Examples: a non-empty stripped name, a non-negative monetary amount, a typed ID
  reference to another aggregate.

### 2.3 Aggregate Root

An **Aggregate Root** is the entry point to a cluster of related entities and value
objects. All external interactions with the cluster go through the root.

- Extends Entity.
- Maintains an internal list of **Domain Events** emitted during state changes.
- Exposes a `collect_events()` method that returns and clears the event list.
- Provides factory methods (`create(...)`) instead of public constructors to enforce
  invariants from the first moment of existence.
- State-change methods enforce business rules and emit domain events before returning.
- Never throws generic errors — only domain-specific exceptions.

### 2.4 Domain Event

A **Domain Event** is an immutable record of something that happened in the domain.

- Named in past tense (e.g., `ItemCreated`, `OrderShipped`).
- Contains only data relevant to the event (the aggregate ID and the changed fields).
- Carries no behavior.
- Collected by the aggregate root; dispatched by the application layer after the
  transaction commits.
- Enables decoupled reactions to state changes without creating direct coupling between
  aggregates.

### 2.5 Domain Exception Hierarchy

All domain errors extend a common base exception class (`DomainError`).

- Sub-types express specific failure scenarios: `NotFoundError`, `ValidationError`,
  `ConflictError`, etc.
- The domain raises these exceptions; the application layer catches them and wraps them
  in a `Result` type; the presentation layer maps them to HTTP status codes.

### 2.6 Outbound Ports (Secondary Ports)

Interfaces defined **inside the domain** that the domain model needs in order to
accomplish its goals, but whose implementation lives in infrastructure.

- **Repository port**: defines the contract for persisting and retrieving aggregates.
  Expressed in domain vocabulary, never in persistence terms (no SQL, no ORM concepts).
  Methods: `save`, `find_by_id`, `find_all`, `find_matching`, `delete`, `count`.
- **Domain event publisher port**: defines a single `publish(event)` contract.
- **Clock port**: defines a `now()` method returning the current instant. Enables
  deterministic time in tests without patching globals.
- **Circuit breaker port**: defines a `call(function, *args)` contract to protect
  outbound calls from cascading failures.

### 2.7 Specification Pattern

A **Specification** is a composable, first-class domain predicate.

- Encapsulates a single business rule in an object with an `is_satisfied_by(candidate)`
  method.
- Composed with boolean operators (AND, OR, NOT) to build complex rules without
  if/else chains scattered across the codebase.
- Used by repository ports to express queries in the domain language; the
  infrastructure adapter translates the specification into the persistence query.
- Satisfies the open/closed principle: new rules are new classes, not modified
  conditions.
- Base combinators (`AndSpecification`, `OrSpecification`, `NotSpecification`) are
  implemented once in the domain and reused for all aggregate types.

### 2.8 Inbound Domain Ports

Interfaces defined inside the domain for **domain-to-domain** communication (e.g., a
domain service that an aggregate calls to compute a derived value, where the
implementation queries an external system).

- Only belong here if they return domain objects or primitives and are called from
  within the domain.
- If they return application DTOs or are called from the presentation layer, they
  belong in the application layer's ports package.

---

## 3. Application Layer Patterns

The application layer orchestrates domain objects to fulfill use cases. It has no
business logic of its own — all invariants live in the domain.

### 3.1 CQRS — Command / Query Responsibility Segregation

The write and read paths are strictly separated.

**Commands**:
- Immutable data objects expressing an intent to change state.
- Carry all data needed to perform the operation (primitive types only, no domain
  objects).
- Named in the imperative mood: `CreateItemCommand`, `UpdateItemCommand`.
- Have an identifier of their own for traceability and idempotency.
- Fields that are optional in the update operation use an explicit strategy (a separate
  boolean flag or a well-defined sentinel in the application layer) to distinguish
  "caller omitted the field" from "caller explicitly set it to null/none".

**Queries**:
- Immutable data objects expressing a read intent.
- Named as questions: `GetItemQuery`, `ListItemsQuery`, `SearchItemsQuery`.
- Return application DTOs, never domain objects.

**Handlers**:
- One handler class per command or query.
- Each handler receives its dependencies via constructor injection (ports only, never
  concrete adapters).
- Returns a `Result[SuccessType, DomainError]` to communicate outcome without
  exceptions crossing layer boundaries.

### 3.2 Result Type (Railway-Oriented Programming)

A typed union `Result[T, E] = Success[T] | Failure[E]` replaces exceptions as the
primary error-signaling mechanism within the application layer.

- `Success` wraps a value of type `T`.
- `Failure` wraps an error of type `E`.
- Both carry `is_success` and `is_failure` boolean properties.
- The application service unwraps the result: on failure it raises the domain error
  so that the presentation layer can handle it via registered exception handlers.
- This keeps the happy path clear and makes error handling explicit at the use-case
  boundary.

### 3.3 Application DTOs and Mappers

**Data Transfer Objects (DTOs)** are plain data containers that cross layer boundaries.

- The application layer defines its own input and output DTOs — it never exposes domain
  objects to the presentation layer.
- **Domain → DTO mapper**: translates aggregate state into a flat, serializable DTO
  after a command completes or a query returns.
- **DTO → Domain mapper**: translates incoming data from the presentation layer into
  domain primitives before invoking domain methods.
- Mappers are stateless functions or classes with no side effects.

### 3.4 Application Inbound Ports (Primary Ports)

Interfaces that define what the application layer offers to the outside world
(presentation, CLI, test harness, etc.).

- Named as services: `IItemApplicationService`.
- Methods correspond to use cases and accept/return DTOs.
- Implemented by **Application Services** (see below).
- The presentation layer depends only on these interfaces, never on concrete classes.

### 3.5 Application Service

Concrete implementation of an inbound port. Acts as the bridge between the presentation
layer and the CQRS handlers.

- Groups all command and query handlers for one aggregate.
- Each public method builds the appropriate command or query, delegates to the handler,
  unwraps the `Result`, and either returns the DTO or raises the domain error.
- Contains no business logic — pure orchestration.

### 3.6 Unit of Work (Application-Level Port)

Defines the contract for grouping repository operations and event publication into a
single transactional boundary.

- Lives in the application layer (not the domain) because it is an orchestration concern,
  not a domain concept.
- Generic over the repository type so one interface serves all aggregates.
- Works as an async context manager: on normal exit it expects an explicit `commit()`
  call; on exception it automatically calls `rollback()`.
- `collect(events)`: enqueues domain events to be published on commit.
- `commit()`: flushes persistence changes and dispatches all collected events.
- Concrete implementations live in infrastructure.

### 3.7 Pagination

Query handlers that return lists wrap their results in a generic `PaginatedResult`
structure containing:
- The data slice for the current page.
- Total count of matching records.
- The requested limit and offset.
- Computed `has_next` and `has_previous` flags for client-side navigation.

---

## 4. Infrastructure Layer Patterns

Infrastructure contains all adapters that implement ports defined in the domain and
application layers.

### 4.1 Repository Adapter

Implements the domain's repository port for a specific persistence technology.

- Translates domain method calls into persistence queries (SQL, document store, etc.).
- Translates raw persistence results back into domain aggregates.
- Translates `Specification` objects into technology-specific query predicates via a
  dedicated **Specification Translator** component, keeping translation logic isolated.
- Never exposed directly to the application or presentation layers.

### 4.2 In-Memory Repository Adapter

A repository adapter that stores aggregates in a plain in-memory data structure.

- Used in unit and integration tests to avoid I/O.
- Implements the exact same port interface as the production adapter.
- Enables the full application layer to be tested without any external dependency.
- Also used as the default backend when no database is configured (useful for local
  development and demos).

### 4.3 Unit of Work Adapter

Implements the application layer's `IUnitOfWork` port.

- Manages session / transaction lifecycle scoped to a single command handler invocation.
- Supports two event-publishing modes:
  - **In-process mode**: commits the persistence transaction first, then dispatches
    domain events synchronously in the same process.
  - **Outbox mode**: writes domain event records into the same persistence transaction
    as the aggregate change, guaranteeing atomicity. A background relay worker
    dispatches them asynchronously.
- The Unit of Work is generic: one implementation class handles any aggregate repository
  by accepting a repository factory at construction time.

### 4.4 Outbox Pattern

Guarantees that domain events are never lost even if the message broker or event
dispatcher is unavailable at commit time.

1. When a command commits, domain event records are written to an **outbox table** in
   the same database transaction as the aggregate change. This is atomic.
2. A background **relay worker** polls the outbox table periodically, reads unpublished
   rows, dispatches them to the downstream publisher, and marks them as published.
3. Delivery guarantee is **at-least-once**: if the relay crashes between dispatch and
   marking, the event will be re-dispatched. Downstream consumers must be idempotent.
4. In multi-worker deployments, the relay uses a `SELECT … FOR UPDATE SKIP LOCKED`
   query (or equivalent) to prevent concurrent workers from processing the same row.

### 4.5 Domain Event Publisher Adapters

Two publisher implementations satisfy the same `IDomainEventPublisher` port:

- **In-process publisher**: dispatches events synchronously to registered handlers
  within the same process. Zero infrastructure needed; ideal for tests and single-process
  deployments.
- **Broker publisher**: serializes events and forwards them to an external message
  broker (e.g., message queue, event streaming platform). Used in production for
  cross-service event propagation.

### 4.6 Authentication Adapter

Implements token verification (e.g., OIDC / JWT) as an infrastructure adapter.

- Accepts the authentication configuration and optionally a circuit breaker port.
- Fetches public keys or JWKS from the identity provider; protected by the circuit
  breaker to avoid cascading failures if the provider is down.
- Returns an application-level `CurrentUser` DTO — presentation layer never sees raw
  token claims.
- If no issuer is configured, the adapter is disabled and all requests are treated as
  anonymous (useful for local development).

### 4.7 Clock Adapter

A concrete implementation of the domain's `IClock` port.

- **System clock**: returns the actual current UTC time.
- **Fake clock**: used in tests. Initialized with a fixed instant; can be advanced
  manually with a `tick(duration)` method for deterministic time-based tests.

### 4.8 Circuit Breaker Adapter

Wraps a third-party circuit breaker library to satisfy the domain's `ICircuitBreaker`
port.

- The domain and application layers depend only on the port interface, not the library.
- Swapping the library requires only a new adapter — zero changes to domain or application.

### 4.9 Observability Adapters

Three independent adapters handle telemetry:

- **Structured logging**: emits JSON log records with contextual fields (trace ID,
  request ID, etc.).
- **Distributed tracing**: instruments the application to emit spans compatible with
  the OpenTelemetry standard. Traces can be exported to any OTLP-compatible backend.
- **Metrics**: exposes runtime and business metrics.

All three adapters are configured from the application settings and activated at startup.

### 4.10 Rate Limiting Adapter

A middleware-level adapter that enforces request rate limits per client.

- Configured via application settings.
- Returns a standard protocol error response (e.g., HTTP 429) when the limit is
  exceeded, without the application or domain layer being aware.

### 4.11 Composition Root

A single **Container** class wires all adapters to all ports.

- Constructed once at application startup.
- Returns per-request or singleton service instances to the presentation layer via
  dependency injection.
- Organized into focused sub-containers (persistence, events, resilience) to avoid a
  monolithic wiring class.
- The only place in the codebase allowed to import from all layers simultaneously.
- Swapping an adapter requires changing only the relevant sub-container — no domain or
  application code changes.

---

## 5. Presentation Layer Patterns

### 5.1 Request Schema / Response Schema

- Input schemas validate and deserialize incoming requests (HTTP bodies, query strings).
- They are distinct from application DTOs: they may include HTTP-specific fields,
  validation decorators, or serialization hints not present in the DTO.
- A **Schema Mapper** translates the validated schema into DTO calls to the application
  service, and maps the output DTO back to the response schema.

### 5.2 Error Handler Registry

- Domain exceptions are mapped to protocol-specific responses in a centralized registry.
- Handlers import exception types only from the **application layer's re-export module**,
  never from the domain directly.
- This keeps the presentation layer oblivious to domain internals; if the domain
  exception hierarchy changes, only the re-export module needs updating.
- One handler per exception type guarantees predictable, uniform error responses.

### 5.3 Middlewares

Cross-cutting HTTP concerns are implemented as middleware, executed for every request
before reaching any route handler:

- **Correlation ID middleware**: generates or propagates a unique request identifier
  that flows through logs, traces, and response headers for end-to-end traceability.
- **Telemetry middleware**: records request/response metadata (method, path, status
  code, duration) as trace spans and metrics.
- **Authentication middleware** (or dependency): verifies tokens and populates the
  current-user context consumed by route handlers.
- **Rate limiting middleware**: enforces per-client request quotas.

### 5.4 Versioned API

Routes are organized under a version prefix (e.g., `/api/v1/`) to allow future
breaking changes without disrupting existing clients.

---

## 6. Testing Strategy

### 6.1 Three-Tier Test Suite

```
tests/
├── unit/          Pure, in-process, no I/O — fast feedback
├── integration/   Adapter contracts + API endpoint tests
└── architecture/  Structural rules verified at runtime
```

**Unit tests** (no I/O):
- Domain tests: aggregate invariants, domain event emission, value object validation.
- Application tests: CQRS handler behavior using in-memory adapters and fake clocks.
- No mocking of domain interfaces — in-memory adapters are used instead, providing
  higher-fidelity tests.

**Integration tests**:
- **Repository contract tests**: the same test suite is executed against every adapter
  (in-memory and real persistence). Both must pass the same set of behavioral assertions.
  This is the **Liskov Substitution Principle** applied to test infrastructure.
- **API endpoint tests**: the full application stack is assembled with an in-memory
  persistence adapter and tested end-to-end via the HTTP interface.

**Architecture tests**:
- Import graph assertions verify the dependency rule at runtime (see Section 7).

### 6.2 Property-Based Testing

Property-based tests complement example-based tests by generating hundreds of arbitrary
inputs and verifying that invariants hold for all of them, not just the hand-picked
cases.

Applied to:
- **Value objects**: for any valid input, the object must be constructed without error
  and store the expected normalized value. For any invalid input, it must raise the
  domain exception. Equality and string representation contracts are verified.
- **Aggregate invariants**: for any valid combination of inputs, the aggregate must be
  created without error and emit the expected events. Specification compositions
  (AND, OR, NOT) must satisfy algebraic laws (commutativity, double-negation identity).

### 6.3 Test Doubles Strategy

| Dependency      | Test double    | Why                                      |
|-----------------|----------------|------------------------------------------|
| Repository      | In-memory impl | Full interface fidelity; shared with production contract tests |
| Clock           | Fake clock     | Deterministic time; controllable advance via `tick()` |
| Event publisher | In-memory impl | Captures published events for assertion  |
| Unit of Work    | In-memory impl | Wraps in-memory repo; no transaction overhead |

No mocking frameworks are used for domain ports. Fake/in-memory implementations
provide stronger contracts and avoid brittle test-to-implementation coupling.

---

## 7. Architectural Guards and Quality Gates

The dependency rule is not enforced by convention alone — three independent automated
tools verify it continuously.

### 7.1 Module Boundary Declarations (Static)

A `tach.toml` (or equivalent) file declares every module, its allowed dependencies, and
explicitly forbids any other dependency. Violations are caught at development time
before code is committed.

```
domain        → depends on: nothing
application   → depends on: domain
infrastructure → depends on: domain, application, settings
presentation  → depends on: application
container     → depends on: all (composition root)
```

### 7.2 Import Contract Checks (Static)

An import linter configuration file (`.importlinter` or equivalent) specifies forbidden
import paths:

- `domain` must not import `application`, `infrastructure`, or `presentation`.
- `application` must not import `infrastructure` or `presentation`.
- `presentation` must not import `infrastructure`.

Violations are reported as linter errors and block the commit.

### 7.3 Runtime Import Graph Assertions (Dynamic)

Architecture tests run as part of the standard test suite and verify the actual import
graph at runtime using an architecture testing library. These tests catch dynamic
imports, conditional imports, or `TYPE_CHECKING`-scoped imports that static tools might
miss.

One test per rule:
- Domain does not import application.
- Domain does not import infrastructure.
- Domain does not import presentation.
- Domain does not import any external persistence framework.
- Domain does not import any external HTTP framework.
- Application does not import infrastructure.
- Application does not import presentation.
- Application does not import any external persistence framework.
- Application does not import any external HTTP framework.
- Presentation does not import infrastructure.
- Presentation does not import domain model directly (only via DTOs).

### 7.4 Strict Static Typing

All code is type-annotated. A strict type checker (equivalent to `mypy --strict`) runs
on every commit and rejects:
- Missing annotations.
- `Any` types introduced without explicit casts.
- Incorrect generic parameter usage.
- Calls to ports with wrong argument types.

### 7.5 Linting and Formatting

- A code formatter enforces consistent style automatically (no style debates).
- A linter checks for code quality issues: unused variables, complex functions,
  naming conventions, missing docstrings on public interfaces.
- Both run automatically on commit; the commit is rejected if they report errors.

### 7.6 Pre-Commit Hooks

All of the above tools are wired to git hooks:

- **On commit**: formatter, linter, tach module check, import linter, architecture tests.
- **On push**: full test suite including integration and property-based tests.

No developer can push code that violates the architectural rules, fails type checking,
or breaks any test.

---

## 8. Cross-Cutting Design Principles

### 8.1 Dependency Inversion Principle (DIP)

High-level modules (domain, application) define abstract interfaces (ports). Low-level
modules (infrastructure, presentation) implement or consume those interfaces. The
direction of source-code dependency is always the opposite of the direction of control
flow for external interactions.

### 8.2 Interface Segregation Principle (ISP)

Ports are narrow and focused. A repository port exposes only the operations the domain
actually needs — not a generic CRUD interface. This keeps adapters small and allows
different adapters to implement different subsets.

### 8.3 Single Responsibility Principle (SRP)

Each class has one reason to change:
- Value objects: validation and normalization of one concept.
- Handlers: orchestration of one use case.
- Adapters: translation between one external system and the domain.
- Mappers: translation between two data representations.

### 8.4 Open/Closed Principle (OCP)

New use cases are added by creating new command/query/handler classes. New persistence
backends are added by creating new adapter classes implementing existing ports. Existing
classes are not modified. The Specification pattern extends query capabilities without
modifying repositories.

### 8.5 Explicit Over Implicit

- Error paths are made explicit via the `Result` type in the application layer.
- The distinction between "field not provided" and "field explicitly set to null" is
  expressed via an explicit boolean flag, not an opaque sentinel.
- Time is injected via a clock interface, not read from a global.
- Configuration is explicit via a typed settings object, not read from environment
  variables scattered throughout the code.

### 8.6 Immutability

- Value objects are always immutable.
- Commands and queries are immutable.
- Domain events are immutable.
- DTOs are immutable.
- Mutation is restricted to aggregate state-change methods that also enforce invariants
  and emit events.

---

## 9. Project Structure Blueprint

```
src/
└── <app_name>/
    ├── domain/
    │   ├── model/
    │   │   ├── entity.py            # Base Entity class
    │   │   ├── aggregate.py         # Base AggregateRoot class
    │   │   ├── value_object.py      # Base ValueObject marker
    │   │   └── <context>/
    │   │       ├── <aggregate>.py         # Aggregate root
    │   │       ├── <aggregate>_events.py  # Domain events
    │   │       └── value_objects.py       # VOs for this aggregate
    │   ├── ports/
    │   │   ├── inbound/             # Domain-to-domain service contracts
    │   │   │   └── clock.py
    │   │   └── outbound/            # Ports the domain needs from infra
    │   │       ├── <aggregate>_repository.py
    │   │       ├── event_publisher.py
    │   │       └── circuit_breaker.py
    │   ├── events/
    │   │   └── base.py              # DomainEvent base class
    │   ├── exceptions/
    │   │   └── domain_errors.py     # DomainError hierarchy
    │   └── specifications/
    │       ├── base.py              # Specification[T] + combinators
    │       └── <aggregate>_specifications.py
    │
    ├── application/
    │   ├── commands/
    │   │   └── <aggregate>_commands.py
    │   ├── queries/
    │   │   └── <aggregate>_queries.py
    │   ├── handlers/
    │   │   ├── command_handlers.py
    │   │   └── query_handlers.py
    │   ├── services/
    │   │   └── <aggregate>_service.py   # Implements inbound port
    │   ├── ports/
    │   │   ├── <aggregate>_application_service.py  # Inbound port
    │   │   └── unit_of_work.py                     # UoW port
    │   ├── dtos/
    │   │   ├── <aggregate>_dtos.py
    │   │   └── pagination.py
    │   ├── mappers/
    │   │   └── <aggregate>_mapper.py
    │   ├── exceptions.py            # Re-exports domain exceptions
    │   └── result.py                # Result[T, E] type
    │
    ├── infrastructure/
    │   ├── persistence/
    │   │   ├── in_memory/           # In-memory adapters (tests + dev)
    │   │   └── <technology>/        # Production adapter (SQL, Mongo, etc.)
    │   ├── events/
    │   │   ├── in_process_publisher.py
    │   │   ├── outbox_publisher.py
    │   │   ├── outbox_relay.py
    │   │   └── broker/              # External broker adapter
    │   ├── auth/                    # Authentication adapter
    │   ├── clock/                   # System clock + fake clock
    │   ├── resilience/              # Circuit breaker adapter
    │   ├── observability/           # Logging, tracing, metrics adapters
    │   ├── rate_limiting/           # Rate limiting adapter
    │   └── di/                      # Sub-containers (persistence, events, resilience)
    │
    ├── presentation/
    │   ├── api/
    │   │   └── v<N>/
    │   │       ├── routers/         # Route handlers per aggregate
    │   │       └── schemas/         # Request/response schemas
    │   ├── mappers/                 # Schema ↔ DTO mappers
    │   ├── middlewares/             # Correlation ID, telemetry, auth
    │   ├── error_handlers.py        # DomainError → HTTP response mapping
    │   └── app_state.py             # Typed dependency injection state
    │
    ├── container.py                 # Composition root
    └── settings.py                  # Typed configuration from environment

tests/
├── unit/
│   ├── domain/                      # Aggregate, VO, specification tests
│   ├── application/                 # Handler tests (in-memory adapters)
│   ├── infrastructure/              # Adapter unit tests
│   └── presentation/               # Error handler, middleware tests
├── integration/
│   ├── infrastructure/              # Repository contract tests (parametrized)
│   └── api/                         # End-to-end HTTP tests
└── architecture/
    ├── test_dependencies.py         # Import graph assertions
    └── test_structure.py            # Directory/naming convention checks
```

---

## 10. How to Add a New Use Case (Checklist)

1. **Domain**: add a method to the aggregate root that enforces the invariant and emits
   a domain event. Add or reuse value objects as needed.
2. **Application — Command**: create an immutable command data object with all required
   fields.
3. **Application — Handler**: create a handler class. Inject the `IUnitOfWork` and any
   other outbound ports via constructor. Implement `handle(command) -> Result[DTO, Error]`.
4. **Application — Service**: add a method to the application service that delegates to
   the handler and unwraps the `Result`.
5. **Application — Inbound Port**: add the method signature to the application service
   interface.
6. **Presentation — Route**: add a route that validates input, calls the application
   service, and maps the DTO to a response schema.
7. **Container**: wire the new handler with its dependencies.
8. **Tests**: add unit tests for the domain method; add handler tests using in-memory
   adapters; the architecture tests guard the new code automatically.

## 11. How to Swap a Persistence Adapter

1. Create a new adapter class implementing the repository port interface.
2. Implement every method in domain terms (not persistence terms).
3. Add a specification translator if the repository supports `find_matching`.
4. Register the adapter in the appropriate sub-container.
5. Run the repository contract test suite — the new adapter must pass the same tests as
   all other adapters.
6. No domain, application, or presentation code changes.

---

*This document is the single authoritative reference for replicating this architecture
in any language. Implement the patterns and guards described here; the specific
libraries, frameworks, and syntax are interchangeable.*
