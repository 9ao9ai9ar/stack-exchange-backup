import pytest
import typing_extensions

from stackexchange.api import StackExchangeApi
from stackexchange.model_extend import (
    BakedInFilter,
    Filter,
    ReadFilterParameters,
)


@pytest.fixture(scope="module")
def defined_filters():
    api = StackExchangeApi()
    # pylint: disable-next=no-member
    baked_in_filters = typing_extensions.get_args(BakedInFilter.__value__)
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
                    "6(Kf1Nok-_lSPXKCtHLJwx-lErW2vKXX0.cTH70g*TOaJsLcz1fY(j_pvVWgk1G",
                    "unsafe",
                    sorted([
                        ".backoff",
                        ".has_more",
                        ".items",
                        ".quota_remaining",
                        "answer.body_markdown",
                        "answer.comments",
                        "answer.creation_date",
                        "answer.down_vote_count",
                        "answer.is_accepted",
                        "answer.owner",
                        "answer.score",
                        "answer.up_vote_count",
                        "comment.body",
                        "comment.body_markdown",
                        "comment.creation_date",
                        "comment.owner",
                        "comment.score",
                        "question.answers",
                        "question.body_markdown",
                        "question.comments",
                        "question.creation_date",
                        "question.down_vote_count",
                        "question.link",
                        "question.owner",
                        "question.question_id",
                        "question.score",
                        "question.title",
                        "question.up_vote_count",
                        "shallow_user.display_name",
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
