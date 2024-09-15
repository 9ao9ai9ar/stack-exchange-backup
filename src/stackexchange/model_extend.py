from annotated_types import MaxLen
from pydantic import (
    ConfigDict,
    PlainSerializer,
    model_serializer,
    model_validator,
)
# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from pydantic_core.core_schema import SerializerFunctionWrapHandler
from typing_extensions import override

# noinspection PyUnresolvedReferences
from stackexchange._model_base import MyBaseModel
# noinspection PyProtectedMember
from stackexchange.generated._model_openapi import *

__all__ = [
    # Component schemas (re-exported from .generated._model_openapi)
    "Answer",
    "Collective",
    "Comment",
    "Error",
    "Filter",
    "NetworkUser",
    "Question",
    "Site",
    "BadgeCount",
    "ClosedDetails",
    "CollectiveExternalLink",
    "CollectiveRecommendation",
    "MigrationInfo",
    "NetworkPost",
    "Notice",
    "OriginalQuestion",
    "RelatedSite",
    "ShallowUser",
    "Styling",
    # Component parameters (re-exported from .generated._model_openapi)
    "Auth",
    "Paging",
    "Complex",
    # Types
    "BuiltInFilter",
    "BakedInFilter",
    # Generic response model
    "Response",
    # Base parameter model
    "ParametersModel",
    # Parameter models
    "QuestionsByIdsParameters",
    "AnswersOnUsersParameters",
    "QuestionsOnUsersParameters",
    "SimulateErrorParameters",
    "CreateFilterParameters",
    "ReadFilterParameters",
    "SitesParameters",
    "AssociatedUsersParameters",
]

type BuiltInFilter = Literal[
    "default",
    "withbody",
    "none",
    "total",
]
type BakedInFilter = Literal[
    "!6aC-iR(QLBu-5SKm",
    "!2SUoF4c)sOul00Zq",
    "6(KgqfEH*wW4Tq__Mn5VGrYXj.xyYJVGEUYpTK4QOaCv8RzhI5qMv6X38J1znyl",
    "!-0ttWpKaHtrB(oS",
]


class Response[T](ResponseWrapper):
    items: Annotated[list[T] | None, Field(fail_fast=True)] = None
    """
    an array of the type found in type
    """


# region Parameter models

# https://www.freecodecamp.org/news/how-to-flatten-a-dictionary-in-python-in-4-different-ways/
def flatten_dict_and_exclude_none_generator(d):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from flatten_dict_and_exclude_none(v).items()
        elif v is not None:
            yield k, v


def flatten_dict_and_exclude_none(d):
    return dict(flatten_dict_and_exclude_none_generator(d))


def list_to_semicolon_delimited_str(lst):
    if isinstance(lst, list):
        return ";".join(str(e) for e in lst)
    else:
        return lst


# https://github.com/pydantic/pydantic/issues/9992
# Model config in inheritance doesn't respect MRO.
class ParametersModel(MyBaseModel):
    model_config = ConfigDict(extra="allow", frozen=False)
    """Extra attributes: ``ignore`` (default), ``allow``, ``forbid``.
    
    When set to ``allow``, additional parameters like 
    `request_id <https://api.stackexchange.com/docs/duplicate-requests>`_ 
    can be added, and validation checks for certain fields can be 
    lifted (e.g. ``pagesize`` on ``/sites`` can exceed 100).
    """
    auth: Auth | None = None
    filter: BuiltInFilter | BakedInFilter | None = None

    @model_serializer(mode="wrap", when_used="unless-none")
    def flatten_and_exclude_none(self, handler: SerializerFunctionWrapHandler):
        return flatten_dict_and_exclude_none(handler(self))

    @model_validator(mode="before")
    @classmethod
    def path_parameters_into_str_batches(cls, data: Any):
        if isinstance(data, dict):
            for k, v in cls.model_fields.items():
                v: FieldInfo
                if v.exclude and v.metadata:
                    for metadata in v.metadata:
                        if (isinstance(metadata, MaxLen)
                                and isinstance(data.get(k), list)):
                            batch_size = metadata.max_length
                            data[k] = [
                                list_to_semicolon_delimited_str(
                                    data[k][i:i + batch_size]
                                )
                                for i in range(0, len(data[k]), batch_size)
                            ]
        return data

    @override
    def model_post_init(self, __context: Any):
        if isinstance(__context, Auth):
            self.auth = __context


class QuestionsByIdsParameters(QuestionsByIdsParametersQuery, ParametersModel):
    ids: Annotated[list[str], Field(exclude=True, max_length=100)]


class AnswersOnUsersParameters(AnswersOnUsersParametersQuery, ParametersModel):
    ids: Annotated[list[str], Field(exclude=True, max_length=100)]


class QuestionsOnUsersParameters(QuestionsOnUsersParametersQuery,
                                 ParametersModel):
    ids: Annotated[list[str], Field(exclude=True, max_length=100)]


class SimulateErrorParameters(SimulateErrorParametersQuery, ParametersModel):
    id: Annotated[int, Field(exclude=True)]


class CreateFilterParameters(CreateFilterParametersQuery, ParametersModel):
    include: Annotated[
        list[str] | None,
        PlainSerializer(list_to_semicolon_delimited_str,
                        when_used="unless-none"),
    ] = None
    exclude: Annotated[
        list[str] | None,
        PlainSerializer(list_to_semicolon_delimited_str,
                        when_used="unless-none"),
    ] = None


class ReadFilterParameters(ReadFilterParametersQuery, ParametersModel):
    filters: Annotated[list[str], Field(exclude=True, max_length=20)]


class SitesParameters(SitesParametersQuery, ParametersModel):
    pass


class AssociatedUsersParameters(AssociatedUsersParametersQuery,
                                ParametersModel):
    ids: Annotated[list[str], Field(exclude=True, max_length=100)]
    types: Annotated[
        list[Literal["main_site", "meta_site"]] | None,
        PlainSerializer(list_to_semicolon_delimited_str,
                        when_used="unless-none"),
    ] = None
    """
    Specify, semicolon delimited, main_site or meta_site to filter by site.
    """

# endregion
