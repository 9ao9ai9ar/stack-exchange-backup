import pytest
from typing_extensions import cast

from stackexchange.api import StackExchangeApi
from stackexchange.model_extend import *


@pytest.fixture(scope="module")
def api():
    return StackExchangeApi()


@pytest.mark.skip("Not yet implemented.")
@pytest.mark.xfail("https://meta.stackexchange.com/q/247899")
def test_parameter_filter_comment_body_markdown_comment_body(api):
    ...


def test_associated_users_parameters_types_meta_site(api):
    params = AssociatedUsersParameters(
        ids=cast(list[str], [1]),
        filter="!-0ttWpKaHtrB(oS",
        paging=Paging(page=1, pagesize=1),
        types=["meta_site"],
    )
    response = next(
        api.associated_users(params, fetch_all=False, items_only=False)
    )
    assert response.total > 1
    if not response.items or not response.has_more:
        pytest.xfail("https://stackapps.com/q/8666/")
