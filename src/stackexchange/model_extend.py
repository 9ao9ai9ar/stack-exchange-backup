import datetime
from dataclasses import dataclass
from typing import TypeAlias, ClassVar

from annotated_types import MaxLen
from pydantic import (
    ConfigDict,
    PlainSerializer,
    field_serializer,
    model_serializer,
    model_validator,
)
from pydantic_core.core_schema import SerializerFunctionWrapHandler
from ruamel.yaml.scalarstring import LiteralScalarString

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
    # Base YAML metadata model
    "MetadataModel",
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
    "r8cwHZB3p97RraWJSdBqs7HCWXUCebDx9Wuhn_ChbmNDTEZ3_1lkd3suiMKEh6U-zwe.EML1(4mmULGTB",
    "!6aC-iR(QLBu-5SKm",
]


class Response[T](ResponseWrapper):
    items: Annotated[list[T] | None, Field(fail_fast=True)] = None
    """
    an array of the type found in type
    """


# region Parameter models

# https://www.freecodecamp.org/news/how-to-flatten-a-dictionary-in-python-in-4-different-ways/
def flatten_dict_and_exclude_none_generator(dct):
    for k, v in dct.items():
        if isinstance(v, dict):
            yield from flatten_dict_and_exclude_none(v).items()
        elif v is not None:
            yield k, v


def flatten_dict_and_exclude_none(dct) -> dict:
    return dict(flatten_dict_and_exclude_none_generator(dct))


def list_to_semicolon_delimited_str(lst: list) -> str:
    return ";".join(str(e) for e in lst)


# https://github.com/pydantic/pydantic/issues/9992
# Model config in inheritance doesn't respect MRO.
class ParametersModel(MyBaseModel):
    model_config: ClassVar[ConfigDict] \
        = ConfigDict(extra="allow", frozen=False)
    """Extra attributes: ``ignore`` (default), ``allow``, ``forbid``.
    
    When set to ``allow``, additional parameters like 
    `request_id <https://api.stackexchange.com/docs/duplicate-requests>`_ 
    can be added, and validation checks for certain fields can be 
    lifted (e.g. ``pagesize`` on ``/sites`` can exceed 100).
    """
    auth: Auth | None = None
    filter: BuiltInFilter | BakedInFilter | None = None

    @model_validator(mode="before")
    @classmethod
    def path_parameters_into_str_batches(cls, data: Any):
        if isinstance(data, dict):
            for k, v in cls.model_fields.items():
                if isinstance(data.get(k), list) and v.exclude and v.metadata:
                    for metadata in v.metadata:
                        if isinstance(metadata, MaxLen):
                            batch_size = metadata.max_length
                            data[k] = [
                                list_to_semicolon_delimited_str(
                                    data[k][i:i + batch_size]
                                )
                                for i in range(0, len(data[k]), batch_size)
                            ]
        return data

    @model_serializer(mode="wrap", when_used="unless-none")
    def flatten_and_exclude_none(self, handler: SerializerFunctionWrapHandler):
        return flatten_dict_and_exclude_none(handler(self))


# https://github.com/pydantic/pydantic/issues/8336
# ids are typed list[int] for validation and list[str] for serialization.
IdsType: TypeAlias = Annotated[
    list[int] | list[str],
    Field(exclude=True, max_length=100),
]


class QuestionsByIdsParameters(QuestionsByIdsParametersQuery, ParametersModel):
    ids: IdsType


class AnswersOnUsersParameters(AnswersOnUsersParametersQuery, ParametersModel):
    ids: IdsType


class QuestionsOnUsersParameters(QuestionsOnUsersParametersQuery,
                                 ParametersModel):
    ids: IdsType


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
    ids: IdsType
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


@dataclass(frozen=True, slots=True)
class ContentLicenseOption:
    name: str
    url: AnyUrl
    starting_date: float
    ending_date: float


# https://meta.stackexchange.com/help/licensing
content_license_options = {
    content_license_option.name: content_license_option
    for content_license_option in (
        ContentLicenseOption(
            "CC BY-SA 4.0",
            AnyUrl("https://creativecommons.org/licenses/by-sa/4.0/"),
            datetime.datetime(2018, 5, 2, tzinfo=datetime.UTC).timestamp(),
            float("infinity"),
        ),
        ContentLicenseOption(
            "CC BY-SA 3.0",
            AnyUrl("https://creativecommons.org/licenses/by-sa/3.0/"),
            datetime.datetime(2011, 4, 8, tzinfo=datetime.UTC).timestamp(),
            datetime.datetime(2018, 5, 2, tzinfo=datetime.UTC).timestamp(),
        ),
        ContentLicenseOption(
            "CC BY-SA 2.5",
            AnyUrl("https://creativecommons.org/licenses/by-sa/2.5/"),
            -float("infinity"),
            datetime.datetime(2011, 4, 8, tzinfo=datetime.UTC).timestamp(),
        ),
    )
}


class MetadataModel(MyBaseModel, extra="ignore"):

    @field_serializer("content_license",
                      return_type=str,
                      when_used="always",
                      check_fields=False)
    def linkify_content_license(self, content_license: str | None) -> str:
        applicable_license = None
        if content_license_option \
                := content_license_options.get(content_license or ""):
            # noinspection PyUnboundLocalVariable
            applicable_license = content_license_option
        elif ((publication_date := getattr(self, "last_edit_date", None))
              or (publication_date := getattr(self, "creation_date", None))):
            # Guess the content license based on its publication date.
            for content_license_option in content_license_options.values():
                if (content_license_option.starting_date
                        <= publication_date
                        < content_license_option.ending_date):
                    applicable_license = content_license_option
                    break
        if applicable_license:
            return (f"[{applicable_license.name}]({applicable_license.url})"
                    + ("" if content_license else "?"))
        elif content_license:
            return content_license
        else:
            return ""


def epoch_time_to_date_str(seconds_since_epoch: int) -> str:
    return (datetime.datetime
            .fromtimestamp(seconds_since_epoch, tz=datetime.UTC)
            .strftime("%Y-%m-%dT%H:%M:%SZ"))


# noinspection PyUnresolvedReferences
DateType: TypeAlias = Annotated[
    int | None,
    PlainSerializer(epoch_time_to_date_str,
                    return_type=str,
                    when_used="unless-none"),
]


class ShallowUserMetadata(MetadataModel):
    display_name: str | None = None
    user_type: str | None = None
    reputation: int | None = None
    link: str | None = None


class CommentMetadata(MetadataModel):
    score: int | None = None
    creation_date: DateType = None
    content_license: str | None = None
    link: str | None = None
    owner: ShallowUserMetadata | None = None
    # pylint: disable=unnecessary-lambda
    body_markdown: Annotated[
        str | None,
        PlainSerializer(lambda s: LiteralScalarString(s),
                        when_used="unless-none"),
    ] = None


class AnswerMetadata(MetadataModel):
    is_accepted: bool | None = None
    awarded_bounty_amount: int | None = None
    score: int | None = None
    up_vote_count: int | None = None
    down_vote_count: int | None = None
    owner: ShallowUserMetadata | None = None
    creation_date: DateType = None
    last_edit_date: DateType = None
    community_owned_date: DateType = None
    content_license: str | None = None
    share_link: str | None = None
    comments: list[CommentMetadata] | None = None


class QuestionMetadata(MetadataModel):
    title: str | None = None
    tags: list[str] | None = None
    view_count: int | None = None
    score: int | None = None
    up_vote_count: int | None = None
    down_vote_count: int | None = None
    owner: ShallowUserMetadata | None = None
    creation_date: DateType = None
    last_edit_date: DateType = None
    community_owned_date: DateType = None
    content_license: str | None = None
    share_link: str | None = None
    comments: list[CommentMetadata] | None = None

# endregion
