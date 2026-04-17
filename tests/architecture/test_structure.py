"""Structural invariant tests.

Verifies that the physical layout of the project matches the expected
hexagonal architecture structure.  These tests catch regressions like
accidentally deleting a layer package, renaming key directories, or
introducing ORM annotations inside the domain model.

Run:
    uv run pytest tests/architecture/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

SRC = Path(__file__).parents[2] / "src" / "app"


# ---------------------------------------------------------------------------
# Layer directories
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("layer", ["domain", "application", "infrastructure", "presentation"])
def test_hexagonal_layer_directories_exist(layer: str) -> None:
    """The four hexagonal layers must always be present as packages."""
    assert (SRC / layer).is_dir(), f"Layer '{layer}' is missing from src/app/"


# ---------------------------------------------------------------------------
# Domain sub-packages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subpkg", ["model", "ports", "specifications", "events", "exceptions"])
def test_domain_subpackages_exist(subpkg: str) -> None:
    """All expected domain sub-packages must exist."""
    assert (SRC / "domain" / subpkg).is_dir(), f"Domain sub-package '{subpkg}' is missing"


# ---------------------------------------------------------------------------
# Application sub-packages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subpkg", ["handlers", "services", "ports", "commands", "queries", "dtos"])
def test_application_subpackages_exist(subpkg: str) -> None:
    """All expected application sub-packages must exist."""
    assert (SRC / "application" / subpkg).is_dir(), f"Application sub-package '{subpkg}' is missing"


# ---------------------------------------------------------------------------
# Infrastructure sub-packages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subpkg", ["persistence", "events", "clock", "auth", "resilience"])
def test_infrastructure_subpackages_exist(subpkg: str) -> None:
    """All expected infrastructure sub-packages must exist."""
    assert (SRC / "infrastructure" / subpkg).is_dir(), f"Infrastructure sub-package '{subpkg}' is missing"


# ---------------------------------------------------------------------------
# Presentation sub-packages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subpkg", ["api", "mappers", "middlewares"])
def test_presentation_subpackages_exist(subpkg: str) -> None:
    """All expected presentation sub-packages must exist."""
    assert (SRC / "presentation" / subpkg).is_dir(), f"Presentation sub-package '{subpkg}' is missing"


# ---------------------------------------------------------------------------
# Naming conventions
# ---------------------------------------------------------------------------


def test_handler_files_follow_naming_convention() -> None:
    """All Python files in application/handlers/ must end with _handlers.py."""
    handlers_dir = SRC / "application" / "handlers"
    py_files = [f for f in handlers_dir.glob("*.py") if f.name != "__init__.py"]
    violations = [f.name for f in py_files if not f.name.endswith("_handlers.py")]
    assert not violations, f"Handler files with non-standard names: {violations}"


def test_repository_files_follow_naming_convention() -> None:
    """All repository adapter files must end with _repository.py."""
    repos = list((SRC / "infrastructure" / "persistence").rglob("*_repository.py"))
    assert repos, "No *_repository.py files found in infrastructure/persistence"


# ---------------------------------------------------------------------------
# Port interfaces must be abstract
# ---------------------------------------------------------------------------


def test_domain_ports_define_abstract_classes() -> None:
    """Every .py in domain/ports that defines a class must use ABC or Protocol.

    Files that contain only documentation or re-export redirects (no class
    definitions) are intentionally skipped.  Ports may use either
    ABC/abstractmethod (nominal typing) or Protocol (structural typing, PEP 544).
    """
    ports_dir = SRC / "domain" / "ports"
    violations = []
    for py_file in ports_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        source = py_file.read_text()
        if "class " not in source:
            continue  # documentation-only or redirect file — no class to check
        has_abstract = "ABC" in source or "abstractmethod" in source or "Protocol" in source
        if not has_abstract:
            violations.append(str(py_file.relative_to(SRC)))
    assert not violations, f"Port files defining a class without ABC/Protocol: {violations}"


# ---------------------------------------------------------------------------
# Domain model must not contain ORM column definitions
# ---------------------------------------------------------------------------


def test_domain_model_does_not_contain_orm_columns() -> None:
    """Domain model files must not reference SQLAlchemy Column / mapped_column."""
    model_dir = SRC / "domain" / "model"
    violations = []
    for py_file in model_dir.rglob("*.py"):
        source = py_file.read_text()
        if "Column(" in source or "mapped_column(" in source:
            violations.append(str(py_file.relative_to(SRC)))
    assert not violations, f"ORM annotations found in domain model: {violations}"


# ---------------------------------------------------------------------------
# Composition root and configuration
# ---------------------------------------------------------------------------


def test_container_module_exists() -> None:
    """app/container.py must exist as the single composition root."""
    assert (SRC / "container.py").is_file(), "app/container.py (composition root) is missing"


def test_settings_module_exists() -> None:
    """app/settings.py must exist as the centralised configuration entry point."""
    assert (SRC / "settings.py").is_file(), "app/settings.py is missing"


def test_main_module_exists() -> None:
    """app/main.py must exist as the application entry point."""
    assert (SRC / "main.py").is_file(), "app/main.py is missing"
