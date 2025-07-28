import warnings
from http import HTTPMethod

import niquests as requests
import pytest

from stackexchange.api import StackExchangeApi
from stackexchange.model_extend import *


@pytest.fixture(scope="module")
def api():
    return StackExchangeApi()


def test_singleton(api):
    api1 = StackExchangeApi(api_key="key", access_token="token")
    api2 = StackExchangeApi(api_key="key", access_token="token")
    assert api is not api1
    assert api2 is api1


def test_simulate_error(api):
    with pytest.raises(requests.HTTPError) as err:
        api.simulate_error(SimulateErrorParameters(id=404))
    assert (hasattr(err.value, "response")
            and err.value.response is not None
            and err.value.response.json() == {
                "error_id": 404,
                "error_name": "no_method",
                "error_message": "simulated",
            })


# An easier alternative to https://api.stackexchange.com/docs/create-filter
# for writing complex filters from scratch.
@pytest.mark.skip("for development purposes only")
def test_create_filter(api):
    new_filter = api.create_filter(
        CreateFilterParameters(
            include=[
                # You should almost always include these fields in the filter:
                ".backoff",
                ".has_more",
                ".items",
                ".quota_remaining",
                # Specify the rest of your include fields below:
            ],
            exclude=[
                # You should almost always exclude these fields in the filter:
                ".total",
                # Specify the rest of your exclude fields below:
            ],
            base="none",
        ),
        http_method=HTTPMethod.POST,
    )
    warnings.warn(UserWarning(repr(new_filter)))
