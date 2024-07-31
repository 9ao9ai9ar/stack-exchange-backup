import argparse
import datetime
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from typing_extensions import TextIO, cast

from stackexchange.api import StackExchangeApi
from stackexchange.model_extend import *

__all__ = [
    "NetworkUserSlim",
    "get_network_users",
    "acquire_missing_network_users",
    "backup_questions",
    "backup_answers",
    "create_markdown_file",
    "create_backup_path",
    "write_question_section",
    "write_answer_sections",
    "write_comment_sections",
]
_api = StackExchangeApi()
MD_DATETIME_FORMAT = "%Y-%m-%d at %H:%M:%S UTC"


@dataclass(frozen=True, kw_only=True)
class NetworkUserSlim:
    site_domain_name: str
    user_id: int


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--account_id",
        type=int,
        required=True,
        help="account id",
    )
    parser.add_argument(
        "--out_dir",
        default="q_and_a",
        type=str,
        help="output directory",
    )
    parser.add_argument(
        "--request_key",
        default=StackExchangeApi.API_KEY,
        type=str,
        help="request key",
    )
    parser.add_argument(
        "--rps",
        default=20,
        type=int,
        help="requests per second limit",
    )
    args = parser.parse_args()
    backup_root = Path(args.out_dir).resolve()
    backup_root.mkdir(exist_ok=True)
    global _api  # pylint: disable=global-statement
    _api = StackExchangeApi(request_key=args.request_key, rps=args.rps)
    network_users = get_network_users(args.account_id)
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
        backup_answers(args.account_id, network_user, backup_root)
        print("Done.")


def get_network_users(account_id: int) -> list[NetworkUserSlim]:
    """

    :param account_id:
    :return:
    """
    associated_users = _api.associated_users(
        AssociatedUsersParameters(
            ids=cast(list[str], [account_id]),
            filter="!2SUoF4c)sOul00Zq",
            types=["main_site", "meta_site"],
        )
    )
    network_users = list[NetworkUserSlim](
        filter(
            None,
            (
                NetworkUserSlim(
                    site_domain_name=associated_user.site_url.host,
                    user_id=associated_user.user_id,
                )
                if associated_user.user_id
                   and associated_user.site_url
                   and associated_user.site_url.host
                else None
                for associated_user in associated_users or []
            )
        )
    )
    acquire_missing_network_users(network_users)
    return network_users


def acquire_missing_network_users(main_site_users: list[NetworkUserSlim]) \
        -> None:
    """
    Apply fix for :meth:`StackExchangeApi.associated_users` not
    returning results for meta sites.

    :param main_site_users:
    :return:
    """
    users_dict = {user.site_domain_name: user.user_id
                  for user in main_site_users}
    for site in _api.sites(SitesParameters()):
        if (site.site_type == "main_site"
                and site.site_url
                and site.site_url.host in users_dict):
            for related_site in site.related_sites or []:
                if (related_site.relation == "meta"
                        and related_site.site_url
                        and related_site.site_url.host
                        # In case the bug gets fixed.
                        and related_site.site_url.host not in users_dict):
                    main_site_users.append(
                        NetworkUserSlim(
                            site_domain_name=related_site.site_url.host,
                            user_id=users_dict[site.site_url.host],
                        )
                    )


def backup_questions(network_user: NetworkUserSlim, backup_root: Path) -> None:
    """

    :param network_user:
    :param backup_root:
    :return:
    """
    f: BakedInFilter = "6(Kf1Nok-_lSPXKCtHLJwx-lErW2vKXX0.cTH70g*TOaJsLcz1fY(j_pvVWgk1G"  # noqa
    questions = _api.questions_on_users(
        QuestionsOnUsersParameters(
            ids=cast(list[str], [network_user.user_id]),
            site=network_user.site_domain_name,
            filter=f,
        )
    )
    for question in questions:
        create_markdown_file(question,
                             backup_root,
                             network_user.site_domain_name,
                             "questions")


def backup_answers(account_id: int,
                   network_user: NetworkUserSlim,
                   backup_root: Path) -> None:
    """

    :param account_id:
    :param network_user:
    :param backup_root:
    :return:
    """
    answers = _api.answers_on_users(
        AnswersOnUsersParameters(
            ids=cast(list[str], [network_user.user_id]),
            site=network_user.site_domain_name,
            filter="!6aC-iR(QLBu-5SKm",
        )
    )
    f: BakedInFilter = "6(Kf1Nok-_lSPXKCtHLJwx-lErW2vKXX0.cTH70g*TOaJsLcz1fY(j_pvVWgk1G"  # noqa
    questions = _api.questions_by_ids(
        QuestionsByIdsParameters(
            ids=cast(list[str],
                     [answer.question_id for answer in answers]),
            site=network_user.site_domain_name,
            filter=f,
        )
    )
    for question in questions:
        if not question.owner or question.owner.account_id != account_id:
            create_markdown_file(question,
                                 backup_root,
                                 network_user.site_domain_name,
                                 "answers")


def create_markdown_file(question: Question,
                         backup_root: str | PathLike[str],
                         *child_paths: str | PathLike[str]) -> None:
    """

    :param question:
    :param backup_root:
    :param child_paths:
    :return:
    """
    md_file = (create_backup_path(backup_root,
                                  *child_paths,
                                  str(question.question_id))
               .with_suffix(".md"))
    # If the file already exists, then skip it to save time.
    if md_file.exists():
        return
    with md_file.open(mode="w", encoding="utf-8") as f:
        write_question_section(f, question)
        write_answer_sections(f, question.answers or [])


def create_backup_path(backup_root: str | PathLike[str],
                       *child_paths: str | PathLike[str]) -> Path:
    """

    :param backup_root:
    :param child_paths:
    :return:
    """
    backup_subfolder = Path(backup_root, *child_paths).resolve()
    backup_subfolder.relative_to(backup_root)
    backup_subfolder.parent.mkdir(parents=True, exist_ok=True)
    return backup_subfolder


def write_question_section(f: TextIO, question: Question) -> None:
    """

    :param f:
    :param question:
    :return:
    """
    f.write(f"Question downloaded from {question.link} \\\n")
    question_creation_date = datetime.datetime.fromtimestamp(
        question.creation_date or 0,
        tz=datetime.UTC
    ).strftime(MD_DATETIME_FORMAT)
    if question.owner and question.owner.display_name:
        f.write(f"Question asked by {question.owner.display_name} on "
                + f"{question_creation_date}.\\\n")
    else:
        f.write(f"Question asked on {question_creation_date}.\\\n")
    f.write(f"Number of up votes: {question.up_vote_count}\\\n")
    f.write(f"Number of down votes: {question.down_vote_count}\\\n")
    f.write(f"Score: {question.score}\n\n")
    f.write(f"# {question.title}\n")
    f.write(f"{question.body_markdown}\n")
    write_comment_sections(f, question.comments or [])


def write_answer_sections(f: TextIO, answers: list[Answer]) -> None:
    """

    :param f:
    :param answers:
    :return:
    """
    for i, answer in enumerate(answers, start=1):
        f.write(f"## Answer {i}\n")
        answer_creation_date = datetime.datetime.fromtimestamp(
            answer.creation_date or 0,
            tz=datetime.UTC
        ).strftime(MD_DATETIME_FORMAT)
        if answer.owner and answer.owner.display_name:
            f.write(f"Answer given by {answer.owner.display_name} on "
                    + f"{answer_creation_date}.\\\n")
        else:
            f.write(f"Answer given on {answer_creation_date}.\\\n")
        if answer.is_accepted:
            f.write("This is the accepted answer.\\\n")
        else:
            f.write("This is not the accepted answer.\\\n")
        f.write(f"Number of up votes: {answer.up_vote_count}\\\n")
        f.write(f"Number of down votes: {answer.down_vote_count}\\\n")
        f.write(f"Score: {answer.score}\n\n")
        f.write(f"{answer.body_markdown}\n")
        write_comment_sections(f, answer.comments or [])


def write_comment_sections(f: TextIO, comments: list[Comment]) -> None:
    """

    :param f:
    :param comments:
    :return:
    """
    for i, comment in enumerate(comments, start=1):
        f.write(f"### Comment {i}\n")
        comment_creation_date = datetime.datetime.fromtimestamp(
            comment.creation_date or 0,
            tz=datetime.UTC
        ).strftime(MD_DATETIME_FORMAT)
        if comment.owner and comment.owner.display_name:
            f.write(f"Comment made by {comment.owner.display_name} on "
                    + f"{comment_creation_date}.\\\n")
        else:
            f.write(f"Comment made on {comment_creation_date}.\\\n")
        f.write(f"Comment score: {comment.score}\n\n")
        f.write(f"{comment.body_markdown}\n")


if __name__ == "__main__":
    main()
