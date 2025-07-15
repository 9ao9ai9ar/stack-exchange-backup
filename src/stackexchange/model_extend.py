import datetime
import re
from typing import override

from annotated_types import MaxLen
from pydantic import (
    ConfigDict,
    PlainSerializer,
    field_serializer,
    model_serializer,
    model_validator,
)
# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from pydantic_core.core_schema import SerializerFunctionWrapHandler
from ruamel.yaml.scalarstring import LiteralScalarString

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
    # YAML metadata models
    "ShallowUserMetadata",
    "CommentMetadata",
    "AnswerMetadata",
    "QuestionMetadata",
]

type BuiltInFilter = Literal[
    "default",
    "withbody",
    "none",
    "total",
]
type BakedInFilter = Literal[
    "!-0ttWpKaHtrB(oS",
    "!2SUoF4c)sOul00Zq",
    "7I-hxO428Vv_b5(ED5z6tCN8LC(R5KOA9xhp7eq*O7EcRIX5*V3bK0VdP(N7MJpu3bt7THBXEQt(koRGNuzs",
    "!6aC-iR(QLBu-5SKm",
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
                        return_type=str,
                        when_used="unless-none"),
    ] = None
    exclude: Annotated[
        list[str] | None,
        PlainSerializer(list_to_semicolon_delimited_str,
                        return_type=str,
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
                        return_type=str,
                        when_used="unless-none"),
    ] = None
    """
    Specify, semicolon delimited, main_site or meta_site to filter by site.
    """


# endregion

# region YAML metadata models

def epoch_time_to_date_str(s: int) -> str:
    return (datetime.datetime
            .fromtimestamp(s, tz=datetime.UTC)
            .strftime("%Y-%m-%dT%H:%M:%SZ"))


def linkify_content_license(self, content_license: str) -> str:
    if (content_license
            and (match := re.search(r"^CC BY-SA (\d+\.\d+)$",
                                    content_license))):
        cc_by_sa_version = match.group(1)
    else:
        # Make a best effort guess at the content licenses
        # in case the `sort` workaround becomes ineffective.
        # The cutoff dates and the available licenses come from
        # https://meta.stackexchange.com/help/licensing.
        if not (getattr(self, "creation_date", None)
                or getattr(self, "last_edit_date", None)):
            return "Unknown"
        cutoff_date_1 = datetime.datetime(2011, 4, 8,
                                          tzinfo=datetime.UTC).timestamp()
        cutoff_date_2 = datetime.datetime(2018, 5, 2,
                                          tzinfo=datetime.UTC).timestamp()
        last_edit_date = self.last_edit_date or self.creation_date
        if last_edit_date < cutoff_date_1:
            cc_by_sa_version = "2.5"
        elif cutoff_date_1 <= last_edit_date < cutoff_date_2:
            cc_by_sa_version = "3.0"
        else:
            cc_by_sa_version = "4.0"
        content_license = f"CC BY-SA {cc_by_sa_version}?"
    return f"[{content_license}](https://creativecommons.org/licenses/by-sa/{cc_by_sa_version}/)"


class ShallowUserMetadata(MyBaseModel, extra="ignore"):
    display_name: str | None = None
    user_type: str | None = None
    reputation: int | None = None
    link: str | None = None


class CommentMetadata(MyBaseModel, extra="ignore"):
    score: int | None = None
    creation_date: Annotated[
        int | None,
        PlainSerializer(epoch_time_to_date_str,
                        return_type=str,
                        when_used="unless-none"),
    ] = None
    content_license: str | None = None
    link: str | None = None
    owner: ShallowUserMetadata | None = None
    # Will run into PydanticSchemaGenerationError without the lambda.
    # pylint: disable=unnecessary-lambda
    body_markdown: Annotated[
        str | None,
        PlainSerializer(lambda s: LiteralScalarString(s),
                        when_used="unless-none"),
    ] = None

    @field_serializer("content_license",
                      return_type=str,
                      when_used="always")
    def serialize_content_license(self, content_license):
        return linkify_content_license(self, content_license)


class AnswerMetadata(MyBaseModel, extra="ignore"):
    is_accepted: bool | None = None
    awarded_bounty_amount: int | None = None
    score: int | None = None
    up_vote_count: int | None = None
    down_vote_count: int | None = None
    owner: ShallowUserMetadata | None = None
    creation_date: Annotated[
        int | None,
        PlainSerializer(epoch_time_to_date_str,
                        return_type=str,
                        when_used="unless-none"),
    ] = None
    last_edit_date: Annotated[
        int | None,
        PlainSerializer(epoch_time_to_date_str,
                        return_type=str,
                        when_used="unless-none"),
    ] = None
    content_license: str | None = None
    share_link: str | None = None
    comments: list[CommentMetadata] | None = None

    @field_serializer("content_license",
                      return_type=str,
                      when_used="always")
    def serialize_content_license(self, content_license):
        return linkify_content_license(self, content_license)


class QuestionMetadata(MyBaseModel, extra="ignore"):
    title: str | None = None
    tags: list[str] | None = None
    view_count: int | None = None
    score: int | None = None
    up_vote_count: int | None = None
    down_vote_count: int | None = None
    owner: ShallowUserMetadata | None = None
    creation_date: Annotated[
        int | None,
        PlainSerializer(epoch_time_to_date_str,
                        return_type=str,
                        when_used="unless-none"),
    ] = None
    last_edit_date: Annotated[
        int | None,
        PlainSerializer(epoch_time_to_date_str,
                        return_type=str,
                        when_used="unless-none"),
    ] = None
    content_license: str | None = None
    share_link: str | None = None
    comments: list[CommentMetadata] | None = None

    @field_serializer("content_license",
                      return_type=str,
                      when_used="always")
    def serialize_content_license(self, content_license):
        return linkify_content_license(self, content_license)

# endregion
