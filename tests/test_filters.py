import typing

import pytest

from stackexchange.api import StackExchangeApi
from stackexchange.model_extend import (
    BakedInFilter,
    Filter,
    ReadFilterParameters,
)


@pytest.fixture(scope="module")
def defined_filters():
    api = StackExchangeApi()
    # pylint: disable=no-member
    baked_in_filters = typing.get_args(BakedInFilter.__value__)
    return list(
        api.read_filter(ReadFilterParameters(filters=list(baked_in_filters)))
    )


@pytest.fixture(scope="module")
def expected_filters():
    return [
        Filter(
            filter=filter_,
            filter_type=filter_type,
            included_fields=included_fields,
        )
        for filter_, filter_type, included_fields in sorted(
            [
                (
                    "!-0ttWpKaHtrB(oS",
                    "safe",
                    sorted([
                        ".backoff",
                        ".has_more",
                        ".items",
                        ".quota_remaining",
                        ".total",
                    ]),
                ),
                (
                    "!2SUoF4c)sOul00Zq",
                    "safe",
                    sorted([
                        ".backoff",
                        ".has_more",
                        ".items",
                        ".quota_remaining",
                        "network_user.site_url",
                        "network_user.user_id",
                    ]),
                ),
                # Due to a bug mentioned in
                # https://meta.stackexchange.com/q/247899,
                # we must also include comment.body in the filter
                # in order to get comment.body_markdown in the response.
                (
                    # noqa pylint: disable=line-too-long
                    "7I-hxO428Vv_b5(ED5z6tCN8LC(R5KOA9xhp7eq*O7EcRIX5*V3bK0VdP(N7MJpu3bt7THBXEQt(koRGNuzs",
                    "unsafe",
                    sorted([
                        ".backoff",
                        ".has_more",
                        ".items",
                        ".quota_remaining",
                        "answer.answer_id",
                        "answer.awarded_bounty_amount",
                        "answer.body_markdown",
                        "answer.comments",
                        "answer.content_license",
                        "answer.creation_date",
                        "answer.down_vote_count",
                        "answer.is_accepted",
                        "answer.last_edit_date",
                        "answer.owner",
                        "answer.question_id",
                        "answer.score",
                        "answer.share_link",
                        "answer.up_vote_count",
                        "comment.body",
                        "comment.body_markdown",
                        "comment.content_license",
                        "comment.creation_date",
                        "comment.link",
                        "comment.owner",
                        "comment.score",
                        "migration_info.other_site",
                        "migration_info.question_id",
                        "question.answers",
                        "question.body_markdown",
                        "question.comments",
                        "question.content_license",
                        "question.creation_date",
                        "question.down_vote_count",
                        "question.last_edit_date",
                        "question.migrated_from",
                        "question.migrated_to",
                        "question.owner",
                        "question.question_id",
                        "question.score",
                        "question.share_link",
                        "question.tags",
                        "question.title",
                        "question.up_vote_count",
                        "question.view_count",
                        "shallow_user.display_name",
                        "shallow_user.link",
                        "shallow_user.reputation",
                        "shallow_user.user_type",
                    ]),
                ),
                (
                    "!6aC-iR(QLBu-5SKm",
                    "safe",
                    sorted([
                        ".backoff",
                        ".has_more",
                        ".items",
                        ".quota_remaining",
                        "answer.question_id",
                    ]),
                ),
            ],
            key=lambda tup: tup[0],
        )
    ]


@pytest.mark.parametrize(
    "defined, expected",
    [("defined_filters", "expected_filters")],
)
def test_filters(defined, expected, request):
    defined = request.getfixturevalue(defined)
    expected = request.getfixturevalue(expected)
    assert defined == expected
