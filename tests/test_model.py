import warnings
from typing import Annotated

import pytest
from pydantic import Field, PlainSerializer
from pydantic_core import ValidationError

from stackexchange.api import StackExchangeApi
# noinspection PyProtectedMember
from stackexchange.model_extend import (
    Paging,
    ParametersModel,
    SitesParameters,
    list_to_semicolon_delimited_str,
)


@pytest.fixture(scope="module")
def api():
    return StackExchangeApi()


@pytest.mark.skipif(SitesParameters.model_config.get("extra") != "allow",
                    reason="extra attributes feature not enabled")
def test_model_extra_fields(api):
    page_size = 2 ** 31 - 2
    params = SitesParameters(page=1, pagesize=page_size)  # type: ignore
    assert getattr(params, "pagesize", None) == page_size
    # The following code sample is just a demonstration of a possible use of
    # extra attributes, the outcome of which should not affect the test result.
    try:
        with pytest.raises(ValidationError):
            SitesParameters(paging=Paging(page=1, pagesize=page_size))
        sites = next(
            api.sites(params, auto_pagination=False, items_only=False)
        )
        assert StackExchangeApi.MAX_PAGE_SIZE < len(sites.items) < page_size
    except BaseException as e:  # noqa pylint: disable=broad-exception-caught
        warnings.warn(UserWarning(f"sample code unexpectedly failed:\n{e}"))


def test_list_to_semicolon_delimited_str():
    class MyModel(ParametersModel):
        ids: Annotated[
            list[int] | list[str],
            PlainSerializer(list_to_semicolon_delimited_str),
        ]

    model = MyModel(ids=[1, 2, 3])
    assert model.model_dump() == {"ids": "1;2;3"}


def test_path_parameters_into_str_batches():
    class MyModel(ParametersModel):
        ids: Annotated[
            list[int] | list[str],
            Field(exclude=True, max_length=4),
        ]

    model = MyModel(ids=[1, 2, 3, 4, 5, 6, 7, 8, 9])
    assert (model.model_dump() == {}
            and model.ids == ["1;2;3;4", "5;6;7;8", "9"])


def test_flatten_dict_and_exclude_none():
    class MyAttributes(ParametersModel):
        att_int: int
        att_bool: bool
        att_opt: str | None = None

    class MyModel(ParametersModel):
        name: str
        att: MyAttributes

    model = MyModel(name="my", att=MyAttributes(att_int=1, att_bool=True))
    assert model.model_dump() == {
        "name": "my",
        "att_int": 1,
        "att_bool": True,
    }
