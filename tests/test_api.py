import niquests as requests
import pytest

from stackexchange.api import StackExchangeApi
from stackexchange.model_extend import *


@pytest.fixture(scope="module")
def api():
    return StackExchangeApi()


def test_singleton():
    api1 = StackExchangeApi(request_key="key", access_token="token")
    api2 = StackExchangeApi(request_key="key", access_token="token")
    api3 = StackExchangeApi(request_key="new_key", access_token="token")
    api4 = StackExchangeApi(request_key="key", access_token="new_token")
    assert api2 is api1
    assert api3 is not api2
    assert api2 is not api4 is not api3


@pytest.mark.skip("Not yet implemented.")
def test_rps():
    ...


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


def test_create_filter(api):
    response = api.create_filter(
        CreateFilterParameters(
            include=[".page", ".page_size", ".total", ".items"],
            exclude=["question.question_id", ".total"],
            base="none",
        )
    )
    assert (response.included_fields
            == sorted([".page", ".page_size", ".items"]))
