import warnings

import pytest
from pydantic import (
    BaseModel,
    Field,
    PlainSerializer,
)
from pydantic_core import ValidationError
from typing_extensions import Annotated, cast

from stackexchange.api import StackExchangeApi
from stackexchange.model_extend import (
    Auth,
    Paging,
    ParametersModel,
    SitesParameters,
)
# noinspection PyProtectedMember
from stackexchange.model_extend import list_to_semicolon_delimited_str


@pytest.fixture(scope="module")
def api():
    return StackExchangeApi()


@pytest.mark.skipif(SitesParameters.model_config.get("extra") != "allow",
                    reason="Extra attributes feature not enabled.")
def test_model_extra_fields(api):
    page_size = 2 ** 31 - 2
    params = SitesParameters(page=1, pagesize=page_size)  # type: ignore
    # noinspection Pydantic
    assert (hasattr(params, "pagesize")
            and params.pagesize == page_size)  # type: ignore
    # The following code sample is just a demonstration of a possible use of
    # extra attributes, the outcome of which should not affect the test result.
    try:
        assert page_size > StackExchangeApi.MAX_PAGE_SIZE
        with pytest.raises(ValidationError):
            SitesParameters(paging=Paging(page=1, pagesize=page_size))
        sites = next(api.sites(params, fetch_all=False, items_only=False))
        assert len(sites.items) > StackExchangeApi.MAX_PAGE_SIZE
    # pylint: disable-next=bare-except
    except:  # noqa
        warnings.warn(UserWarning("Sample code unexpectedly failed."))


def test_list_to_semicolon_delimited_str():
    class MyModel(BaseModel):
        ids: Annotated[
            list[int],
            PlainSerializer(list_to_semicolon_delimited_str),
        ]

    model = MyModel(ids=[1, 2, 3])
    assert model.model_dump() == {"ids": "1;2;3"}


def test_flatten_dict_and_exclude_none():
    class MyAttributes(BaseModel):
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


def test_path_parameters_into_str_batches():
    class MyModel(ParametersModel):
        ids: Annotated[
            list[str],
            Field(exclude=True, max_length=4),
        ]

    model = MyModel(ids=cast(list[str], [1, 2, 3, 4, 5, 6, 7, 8, 9]))
    assert model.model_dump() == {}
    assert model.ids == ["1;2;3;4", "5;6;7;8", "9"]


def test_model_post_init():
    class MyModel(ParametersModel):
        pass

    model = MyModel()
    assert model.model_dump() == {}
    model.model_post_init(Auth(key="invalid"))
    assert model.model_dump() == {"key": "invalid"}
