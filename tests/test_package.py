"""Smoke tests for the package scaffold."""

import ranops
import ranops.core


def test_package_imports() -> None:
    assert ranops.__name__ == "ranops"
    assert ranops.core.__name__ == "ranops.core"
