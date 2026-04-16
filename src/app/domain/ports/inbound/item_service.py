"""Inbound ports — not defined in the domain layer.

Primary ports (driving ports) define the API that the presentation layer
calls into the application.  They belong in the **application** layer,
not the domain layer, which only defines what it *needs* from the outside
(outbound / driven ports such as IItemRepository).

The canonical inbound port for items lives at:

    app.application.ports.item_application_service.IItemApplicationService
"""
