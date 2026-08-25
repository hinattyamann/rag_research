"""Smoke tests for the initial development environment."""

import rag_research


def test_package_is_importable() -> None:
    """The project package can be imported from the src directory."""
    assert rag_research.__version__ == "0.1.0"
