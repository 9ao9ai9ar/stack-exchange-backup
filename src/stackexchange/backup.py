from argparse import (
    ArgumentParser,
    ArgumentTypeError,
    Namespace,
)
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Literal, cast

from ruamel.yaml import YAML

from stackexchange.api import StackExchangeApi
from stackexchange.model_extend import *

__all__ = [
    "NetworkUserSlim",
    "get_network_users",
    "acquire_missing_network_users",
    "backup_questions",
    "backup_answers",
    "get_post_dir",
    "create_markdown_file",
]

_api = StackExchangeApi()
yaml = YAML(pure=True)


@dataclass(frozen=True, kw_only=True, slots=True)
class NetworkUserSlim:
    site_domain_name: str
    user_id: int


def main() -> None:
    args = parse_arguments()
    backup_root = Path(args.out_dir, f"stack_user_{args.account_id}").resolve()
    backup_root.mkdir(exist_ok=True)
    global _api  # pylint: disable=global-statement
    _api = StackExchangeApi(api_key=args.api_key, limit_rate=args.limit_rate)
    network_users = get_network_users(args.account_id, args.no_meta)
    print(f"Found {len(network_users)} Stack Exchange sites associated with "
          + f"https://stackexchange.com/users/{args.account_id}/")
    for i, network_user in enumerate(network_users, start=1):
        print("Downloading and writing questions from site "
              + f"{i}/{len(network_users)} "
              + f"({network_user.site_domain_name})...",
              end="",
              flush=True)
        backup_questions(network_user, backup_root)
        print("Done.")
        print("Downloading and writing answers from site "
              + f"{i}/{len(network_users)} "
              + f"({network_user.site_domain_name})...",
              end="",
              flush=True)
        backup_answers(network_user, backup_root)
        print("Done.")


def parse_arguments() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument(
        "--account-id",
        type=int,
        required=True,
        help="account ID",
    )
    parser.add_argument(
        "--out-dir",
        default=".",
        type=str,
        help="output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--no-meta",
        action="store_true",
        help="do not back up posts on meta sites",
    )
    parser.add_argument(
        "--api-key",
        default=StackExchangeApi.API_KEY,
        type=str,
        help="API key",
    )
    parser.add_argument(
        "--limit-rate",
        default=10,
        type=int,
        help="Maximum request rate in requests per second (default: %(default)d)",
    )
    args = parser.parse_args()
    validate_parsed_arguments(args)
    return args


def validate_parsed_arguments(args: Namespace) -> None:
    if not 0 < args.limit_rate <= StackExchangeApi.MAX_REQUESTS_PER_SECOND:
        raise ArgumentTypeError(f"invalid int value: '{args.limit_rate}'")


def get_network_users(account_id: int, no_meta: bool) -> set[NetworkUserSlim]:
    """

    :param account_id:
    :param no_meta:
    :return:
    """
    associated_users = _api.associated_users(
        AssociatedUsersParameters(
            ids=[account_id],
            filter="!2SUoF4c)sOul00Zq",
            types=cast(list[Literal["main_site", "meta_site"]],
                       ["main_site"] if no_meta
                       else ["main_site", "meta_site"]),
        )
    )
    network_users = set[NetworkUserSlim](
        NetworkUserSlim(
            site_domain_name=associated_user.site_url.host,
            user_id=associated_user.user_id,
        )
        for associated_user in associated_users
        if associated_user.user_id
        and associated_user.site_url
        and associated_user.site_url.host
        and (not no_meta or associated_user.site_url.host not in
             ("meta.stackexchange.com", "stackapps.com"))
    )
    if not no_meta:
        acquire_missing_network_users(network_users)
    return network_users


def acquire_missing_network_users(network_users: set[NetworkUserSlim]) -> None:
    """
    Apply fix for :meth:`StackExchangeApi.associated_users` not
    returning results for meta sites.

    :param network_users:
    :return:
    """
    users_dict = {user.site_domain_name: user.user_id
                  for user in network_users}
    for site in _api.sites(SitesParameters()):
        if (site.site_type == "main_site"
                and site.site_url
                and site.site_url.host in users_dict):
            for related_site in site.related_sites or []:
                if (related_site.relation == "meta"
                        and related_site.site_url
                        and related_site.site_url.host):
                    network_users.add(
                        NetworkUserSlim(
                            site_domain_name=related_site.site_url.host,
                            user_id=users_dict[site.site_url.host],
                        )
                    )


def backup_questions(network_user: NetworkUserSlim,
                     backup_root: str | PathLike[str]) -> None:
    """

    :param network_user:
    :param backup_root:
    :return:
    """
    f = "r8cwHZB3p97RraWJSdBqs7HCWXUCebDx9Wuhn_ChbmNDTEZ3_1lkd3suiMKEh6U-zwe.EML1(4mmULGTB"
    questions = _api.questions_on_users(
        QuestionsOnUsersParameters(
            ids=[network_user.user_id],
            site=network_user.site_domain_name,
            filter=f,
        )
    )
    for question in questions:
        create_markdown_file(network_user, question, backup_root, "q")
        for answer in question.answers or []:
            create_markdown_file(network_user, answer, backup_root, "q")


def backup_answers(network_user: NetworkUserSlim,
                   backup_root: str | PathLike[str]) -> None:
    """

    :param network_user:
    :param backup_root:
    :return:
    """
    answers = _api.answers_on_users(
        AnswersOnUsersParameters(
            ids=[network_user.user_id],
            site=network_user.site_domain_name,
            filter="!6aC-iR(QLBu-5SKm",
        )
    )
    not_my_question_ids = [
        answer.question_id
        for answer in answers
        if answer.question_id is not None
           and not (get_post_dir(network_user, answer, backup_root, "q")
                    .exists())
    ]
    if not not_my_question_ids:
        return
    f = "r8cwHZB3p97RraWJSdBqs7HCWXUCebDx9Wuhn_ChbmNDTEZ3_1lkd3suiMKEh6U-zwe.EML1(4mmULGTB"
    questions = _api.questions_by_ids(
        QuestionsByIdsParameters(
            ids=not_my_question_ids,
            site=network_user.site_domain_name,
            filter=f,
        )
    )
    for question in questions:
        create_markdown_file(network_user, question, backup_root, "a")
        for answer in question.answers or []:
            create_markdown_file(network_user, answer, backup_root, "a")


def get_post_dir(network_user: NetworkUserSlim,
                 post: Question | Answer,
                 backup_root: str | PathLike[str],
                 contribution_type: Literal["a", "q"]) -> Path:
    """

    :param network_user:
    :param post:
    :param backup_root:
    :param contribution_type:
    :return:
    """
    post_dir = (Path(backup_root,
                     network_user.site_domain_name,
                     contribution_type,
                     str(post.question_id))
                .resolve())
    post_dir.relative_to(backup_root)
    return post_dir


def create_markdown_file(network_user: NetworkUserSlim,
                         post: Question | Answer,
                         backup_root: str | PathLike[str],
                         contribution_type: Literal["a", "q"]) -> None:
    """

    :param network_user:
    :param post:
    :param backup_root:
    :param contribution_type:
    :return:
    """
    md_name = "index" if isinstance(post, Question) else str(post.answer_id)
    post_dir = get_post_dir(network_user, post, backup_root, contribution_type)
    md_file = Path(post_dir, md_name).with_suffix(".md")
    md_file.parent.mkdir(parents=True, exist_ok=True)
    with md_file.open(mode="w", encoding="utf-8", newline="") as f:
        if isinstance(post, Question):
            frontmatter = (QuestionMetadata
                           .model_validate(post.model_dump())
                           .model_dump())
        else:
            frontmatter = (AnswerMetadata
                           .model_validate(post.model_dump())
                           .model_dump())
        if frontmatter:
            global yaml  # pylint: disable=global-statement
            try:
                yaml.dump(frontmatter, f, transform=lambda s: f"---\n{s}---\n")
            except:  # noqa pylint: disable=bare-except
                # https://yaml.dev/doc/ruamel.yaml/api/#top
                yaml = YAML(pure=True)
        if post.body_markdown:
            f.write(post.body_markdown)


if __name__ == "__main__":
    main()
