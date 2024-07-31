"""
Tests in test_api_known_bugs.py that are now passing due to the Stack
Exchange API being patched are migrated to this module to check for
regression bugs.
"""
import pytest

from stackexchange.api import StackExchangeApi

pytestmark = pytest.mark.skip("This is a stub.")


@pytest.fixture(scope="module")
def api():
    return StackExchangeApi()


def test_regression_1(api):
    ...
