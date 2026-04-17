"""Infrastructure dependency-injection sub-containers.

Each sub-container owns one infrastructure concern:

* PersistenceContainer  — engine, session factory, repositories, health checks
* EventsContainer       — event broker, publishers, outbox relay
* ResilienceContainer   — circuit breaker

The root ``Container`` (app.container) composes these three.
"""
