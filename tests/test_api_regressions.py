"""
Tests in test_api_known_bugs.py that are now passing due to the Stack
Exchange API being patched are migrated to this module to check for
regression bugs.
"""
import pytest

from stackexchange.api import StackExchangeApi


@pytest.fixture(scope="module")
def api():
    return StackExchangeApi()
