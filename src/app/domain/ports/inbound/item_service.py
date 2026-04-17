"""Domain inbound ports — driving ports at the domain boundary.

In Hexagonal Architecture, *inbound ports* (also called *driving ports* or
*primary ports*) define the API through which the outside world drives the
hexagon.  There are two levels:

Application-level inbound ports (canonical location)
-----------------------------------------------------
The primary inbound port for the application use-cases lives at:

    app.application.ports.item_application_service.IItemApplicationService

The ``application`` layer defines these ports because they represent
use-case contracts — they are the entry point for driving adapters
(e.g., HTTP, CLI, gRPC) and return application DTOs, not domain objects.

Domain-level inbound ports (this package)
-----------------------------------------
This package is reserved for *pure domain services* — ports that define
contracts between domain aggregates or bounded contexts, without any
application-layer orchestration (no DTOs, no command/query objects).

Examples of what belongs here:

* ``IPricingService`` — a domain service interface that an aggregate calls
  to compute a derived price, implemented by an infra adapter that queries
  an external pricing engine.

* ``ICurrencyConverter`` — a domain service that converts monetary values;
  defined here so the domain model can call it without knowing the
  implementation.

* ``IInventoryPort`` — an inbound port consumed by another bounded context
  to query stock levels directly from the domain model (domain-to-domain
  communication).

Rule: if the port returns domain objects or primitives and is called
*from within* the domain or *between* aggregates, it belongs here.
If it returns DTOs and is called by the presentation layer, it belongs
in ``app.application.ports``.
"""
