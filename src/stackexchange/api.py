import collections
import datetime
import functools
import inspect
import threading
import time
from collections.abc import Callable, Generator
from http import HTTPMethod

import niquests as requests
from pydantic import SecretStr
from typing_extensions import Literal, overload

from stackexchange.model_extend import *

__version__ = "2.3"
__all__ = ["StackExchangeApi"]


# https://stackoverflow.com/q/6760685
# https://gist.github.com/wowkin2/3af15bfbf197a14a2b0b2488a1e8c787
class SingletonMeta(type):
    _instances = {}
    _init = {}

    # noinspection PyUnusedLocal
    def __init__(cls, clsname, bases, dct):
        super().__init__(type)
        cls._init[cls] = dct.get("__init__", None)

    def __call__(cls, *args, **kwargs):
        init = cls._init[cls]
        if init is not None:
            callargs = (inspect.getcallargs(init, None, *args, **kwargs)
                        .items())
            key = (cls, frozenset(callargs))
        else:
            key = cls
        if key not in cls._instances:
            cls._instances[key] = (super(SingletonMeta, cls)
                                   .__call__(*args, **kwargs))
        return cls._instances[key]

    def __new__(mcs, clsname, bases, dct, **kwds):
        return (super(SingletonMeta, mcs)
                .__new__(mcs, clsname, bases, dct, **kwds))


class StackExchangeApi(metaclass=SingletonMeta):
    API_ROOT = f"https://api.stackexchange.com/{__version__}"
    API_KEY = "YLTVFmHkeJbm7ZIOoXstag(("
    MAX_PAGE_SIZE = 100
    MAX_REQUESTS_PER_SECOND = 30
    """If a single IP is making more than 30 requests a second, new 
    requests will be dropped.
    """
    MAX_CONCURRENT_REQUESTS = 1
    """Just being conservative here, as the exact rate limit mechanisms 
    are not well-understood.
    """

    def __init__(self,
                 request_key=API_KEY,
                 access_token=None,
                 rps=MAX_REQUESTS_PER_SECOND):
        self._request_key: str | None = request_key
        """Request keys, also known as API keys or app keys,
        grant more requests per day (10,000 vs 300 for anonymous API 
        access) and allow querying results past page 25.
        """
        self._access_token: SecretStr | None = access_token
        self._rps: int = rps
        self._rps_deque: collections.deque[int] = collections.deque(
            [0] * StackExchangeApi.MAX_CONCURRENT_REQUESTS,
            maxlen=StackExchangeApi.MAX_CONCURRENT_REQUESTS,
        )
        self._rps_timer = threading.Thread(target=self._refill_rps_deque,
                                           name="Thread-RPS-Timer",
                                           daemon=True)
        self._rps_timer.start()
        self._backoff: dict[str, int] = {}
        """
        `Documentation <https://api.stackexchange.com/docs/throttle>`_:
        A dynamic throttle is also in place on a per-method level.
        If an application receives a response with the backoff field 
        set, it must wait that many seconds before hitting the same 
        method again.
        All methods (even seemingly trivial ones) may return backoff.
        """
        self.session = requests.Session()
        self.session.request = RequestHooks(self.session.request, self)

    @staticmethod
    def check_response(response: requests.models.Response) -> None:
        if not response.ok:
            x_headers = {
                k: v for k, v in response.oheaders.to_dict().lower_items()
                if k in (
                    "x_request_guid",
                    "x_route_name",
                    "x_error_status",
                    "x_error_name",
                    "x_error_message",
                )
            }
            raise requests.HTTPError(x_headers, response=response)

    @staticmethod
    def check_quota_remaining(response: Response) -> None:
        if (response.quota_remaining is not None
                and response.quota_remaining <= 0):
            print("We've reached the daily quota of the Stack Exchange API. "
                  + "The program will resume automatically in 24 hours, "
                  + "or you can press Ctrl+C to abort the pending operation.",
                  flush=True)
            time.sleep(24 * 60 * 60)

    @classmethod
    def get_api_name(cls) -> str:
        current_frame = inspect.currentframe()
        # noinspection PyUnboundLocalVariable
        while (current_frame
               and (f_code := current_frame.f_code)
               and (
                       not f_code.co_qualname.startswith(cls.__name__)
                       or isinstance(cls.__dict__.get(f_code.co_name),
                                     (staticmethod, classmethod))
                       or f_code.co_name.startswith("_")
               )):
            current_frame = current_frame.f_back
        if not current_frame:
            return "undefined"
        else:
            return current_frame.f_code.co_name

    def _refill_rps_deque(self) -> None:
        while True:
            time.sleep(1 / self._rps)
            self._rps_deque.appendleft(0)

    def _check_backoff(self, api_name: str) -> None:
        if self._backoff.get(api_name) is not None:
            now_timestamp = datetime.datetime.now(datetime.UTC).timestamp()
            backoff_timestamp = self._backoff.pop(api_name)
            # Add 1 more second just to be safe
            wait_seconds = round(backoff_timestamp - now_timestamp) + 1
            if wait_seconds > 0:
                print(
                    "We've made too many requests to the Stack Exchange API, "
                    + f"so we will need to wait for {wait_seconds} seconds. "
                    + "Please be patient...",
                    flush=True,
                )
                time.sleep(wait_seconds)

    def _model_post_init(self, params: ParametersModel) -> None:
        if params.auth is None:
            params.model_post_init(Auth(key=self._request_key,
                                        access_token=self._access_token))

    # noinspection PyTypeChecker
    def _parse_response[T](self,
                           response: requests.models.Response,
                           model: T) -> Response["model"]:
        parsed = (Response[model]
                  .model_validate_json(response.content, strict=True))
        self._update_backoff(StackExchangeApi.get_api_name(), parsed)
        StackExchangeApi.check_quota_remaining(parsed)
        return parsed

    def _update_backoff(self, api_name: str, response: Response) -> None:
        if response.backoff:
            self._backoff[api_name] \
                = round(datetime.datetime.now(datetime.UTC).timestamp()
                        + response.backoff)

    @overload
    def questions_by_ids(self,
                         /,
                         params: QuestionsByIdsParameters,
                         *,
                         fetch_all: bool = ...,
                         items_only: Literal[False]) \
            -> Generator[Response[Question], None, None]:
        pass

    @overload
    def questions_by_ids(self,
                         /,
                         params: QuestionsByIdsParameters,
                         *,
                         fetch_all: bool = ...,
                         items_only: Literal[True] = ...) \
            -> Generator[Question, None, None]:
        pass

    def questions_by_ids(self,
                         /,
                         params: QuestionsByIdsParameters,
                         *,
                         fetch_all=True,
                         items_only=True) \
            -> Generator[Response[Question] | Question, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/questions-by-ids>`_
        Returns the questions identified in {ids}.

        :param params:
        :param fetch_all:
        :param items_only:
        :return:
        """
        stop = len(params.ids) if fetch_all else 1
        for ids in params.ids[:stop]:
            url = f"{StackExchangeApi.API_ROOT}/questions/{ids}"
            if fetch_all:
                params = params.model_copy(
                    update=Paging(page=1,
                                  pagesize=StackExchangeApi.MAX_PAGE_SIZE)
                    .model_dump(),
                )
            response = self.session.get(url, params=params)
            parsed = self._parse_response(response, Question)
            if items_only:
                yield from parsed.items or []
            else:
                yield parsed

    @overload
    def answers_on_users(self,
                         /,
                         params: AnswersOnUsersParameters,
                         *,
                         fetch_all: bool = ...,
                         items_only: Literal[False]) \
            -> Generator[Response[Answer], None, None]:
        pass

    @overload
    def answers_on_users(self,
                         /,
                         params: AnswersOnUsersParameters,
                         *,
                         fetch_all: bool = ...,
                         items_only: Literal[True] = ...) \
            -> Generator[Answer, None, None]:
        pass

    def answers_on_users(self,
                         /,
                         params: AnswersOnUsersParameters,
                         *,
                         fetch_all=True,
                         items_only=True) \
            -> Generator[Response[Answer] | Answer, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/answers-on-users>`_
        Returns the answers the users in {ids} have posted.

        :param params:
        :param fetch_all:
        :param items_only:
        :return:
        """
        stop = len(params.ids) if fetch_all else 1
        for ids in params.ids[:stop]:
            url = f"{StackExchangeApi.API_ROOT}/users/{ids}/answers"
            page = 0
            has_more = True
            while has_more:
                page += 1
                if fetch_all:
                    params = params.model_copy(
                        update=Paging(page=page,
                                      pagesize=StackExchangeApi.MAX_PAGE_SIZE)
                        .model_dump(),
                    )
                response = self.session.get(url, params=params)
                parsed = self._parse_response(response, Answer)
                has_more = fetch_all and (parsed.has_more or parsed.items)
                if items_only:
                    yield from parsed.items or []
                else:
                    yield parsed

    @overload
    def questions_on_users(self,
                           /,
                           params: QuestionsOnUsersParameters,
                           *,
                           fetch_all: bool = ...,
                           items_only: Literal[False]) \
            -> Generator[Response[Question], None, None]:
        pass

    @overload
    def questions_on_users(self,
                           /,
                           params: QuestionsOnUsersParameters,
                           *,
                           fetch_all: bool = ...,
                           items_only: Literal[True] = ...) \
            -> Generator[Question, None, None]:
        pass

    def questions_on_users(self,
                           /,
                           params: QuestionsOnUsersParameters,
                           *,
                           fetch_all=True,
                           items_only=True) \
            -> Generator[Response[Question] | Question, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/questions-on-users>`_
        Gets the questions asked by the users in {ids}.

        :param params:
        :param fetch_all:
        :param items_only:
        :return:
        """
        stop = len(params.ids) if fetch_all else 1
        for ids in params.ids[:stop]:
            url = f"{StackExchangeApi.API_ROOT}/users/{ids}/questions"
            page = 0
            has_more = True
            while has_more:
                page += 1
                if fetch_all:
                    params = params.model_copy(
                        update=Paging(page=page,
                                      pagesize=StackExchangeApi.MAX_PAGE_SIZE)
                        .model_dump(),
                    )
                response = self.session.get(url, params=params)
                parsed = self._parse_response(response, Question)
                has_more = fetch_all and (parsed.has_more or parsed.items)
                if items_only:
                    yield from parsed.items or []
                else:
                    yield parsed

    def simulate_error(self, /, params: SimulateErrorParameters) -> Response:
        """`Documentation <https://api.stackexchange.com/docs/simulate-error>`_
        This method allows you to generate an error.

        :param params:
        :return:
        """
        response = self.session.get(
            f"{StackExchangeApi.API_ROOT}/errors/{params.id}",
            params=params,
        )
        parsed = self._parse_response(response, Error)
        return parsed

    @overload
    def create_filter(self,
                      /,
                      params: CreateFilterParameters,
                      *,
                      items_only: Literal[False]) \
            -> Response[Filter]:
        pass

    @overload
    def create_filter(self,
                      /,
                      params: CreateFilterParameters,
                      *,
                      items_only: Literal[True] = ...) \
            -> Filter:
        pass

    def create_filter(self,
                      /,
                      params: CreateFilterParameters,
                      *,
                      items_only=True) \
            -> Response[Filter] | Filter:
        """`Documentation <https://api.stackexchange.com/docs/create-filter>`_
        Creates a new filter given a list of includes, excludes, a base
        filter, and whether or not this filter should be "unsafe".

        When building filters, refer to the fields of the
        common wrapper object with a leading "."

        :param params:
        :param items_only:
        :return:
        """
        response = self.session.get(
            f"{StackExchangeApi.API_ROOT}/filters/create",
            params=params,
        )
        parsed = self._parse_response(response, Filter)
        if items_only:
            if parsed.items:
                return parsed.items[0]
            else:
                raise ValueError("Unexpected exception.", parsed)
        else:
            return parsed

    @overload
    def read_filter(self,
                    /,
                    params: ReadFilterParameters,
                    *,
                    fetch_all: bool = ...,
                    items_only: Literal[False]) \
            -> Generator[Response[Filter], None, None]:
        pass

    @overload
    def read_filter(self,
                    /,
                    params: ReadFilterParameters,
                    *,
                    fetch_all: bool = ...,
                    items_only: Literal[True] = ...) \
            -> Generator[Filter, None, None]:
        pass

    def read_filter(self,
                    /,
                    params: ReadFilterParameters,
                    fetch_all=True,
                    items_only=True) \
            -> Generator[Response[Filter] | Filter, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/read-filter>`_
        Returns the fields included by the given filters,
        and the "safeness" of those filters.

        :param params:
        :param fetch_all:
        :param items_only:
        :return:
        """
        stop = len(params.filters) if fetch_all else 1
        for filters in params.filters[:stop]:
            url = f"{StackExchangeApi.API_ROOT}/filters/{filters}"
            if fetch_all:
                params = params.model_copy(
                    update=Paging(page=1,
                                  pagesize=StackExchangeApi.MAX_PAGE_SIZE)
                    .model_dump(),
                )
            response = self.session.get(url, params=params)
            parsed = self._parse_response(response, Filter)
            if items_only:
                yield from parsed.items or []
            else:
                yield parsed

    @overload
    def sites(self,
              /,
              params: SitesParameters,
              *,
              fetch_all: bool = ...,
              items_only: Literal[False]) \
            -> Generator[Response[Site], None, None]:
        pass

    @overload
    def sites(self,
              /,
              params: SitesParameters,
              *,
              fetch_all: bool = ...,
              items_only: Literal[True] = ...) \
            -> Generator[Site, None, None]:
        pass

    def sites(self,
              /,
              params: SitesParameters,
              *,
              fetch_all=True,
              items_only=True) \
            -> Generator[Response[Site] | Site, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/sites>`_
        Returns all sites in the network.

        :param params:
        :param fetch_all:
        :param items_only:
        :return:
        """
        page = 0
        has_more = True
        while has_more:
            page += 1
            if fetch_all:
                params = params.model_copy(
                    update=Paging(page=page,
                                  pagesize=StackExchangeApi.MAX_PAGE_SIZE)
                    .model_dump(),
                )
            response = self.session.get(f"{StackExchangeApi.API_ROOT}/sites",
                                        params=params)
            parsed = self._parse_response(response, Site)
            has_more = fetch_all and (parsed.has_more or parsed.items)
            if items_only:
                yield from parsed.items or []
            else:
                yield parsed

    @overload
    def associated_users(self,
                         /,
                         params: AssociatedUsersParameters,
                         *,
                         fetch_all: bool = ...,
                         items_only: Literal[False]) \
            -> Generator[Response[NetworkUser], None, None]:
        pass

    @overload
    def associated_users(self,
                         /,
                         params: AssociatedUsersParameters,
                         *,
                         fetch_all: bool = ...,
                         items_only: Literal[True] = ...) \
            -> Generator[NetworkUser, None, None]:
        pass

    def associated_users(self,
                         /,
                         params: AssociatedUsersParameters,
                         *,
                         fetch_all=True,
                         items_only=True) \
            -> Generator[Response[NetworkUser] | NetworkUser, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/associated-users>`_
        Returns all of a user's associated accounts,
        given their account_ids in {ids}.
        It is a `known bug <https://stackapps.com/q/8666/>`_ that
        results are not returned for meta sites.

        :param params:
        :param fetch_all:
        :param items_only:
        :return:
        """
        stop = len(params.ids) if fetch_all else 1
        for ids in params.ids[:stop]:
            url = f"{StackExchangeApi.API_ROOT}/users/{ids}/associated"
            page = 0
            has_more = True
            while has_more:
                page += 1
                if fetch_all:
                    params = params.model_copy(
                        update=Paging(page=page,
                                      pagesize=StackExchangeApi.MAX_PAGE_SIZE)
                        .model_dump(),
                    )
                response = self.session.get(url, params=params)
                parsed = self._parse_response(response, NetworkUser)
                has_more = fetch_all and (parsed.has_more or parsed.items)
                if items_only:
                    yield from parsed.items or []
                else:
                    yield parsed


class RequestHooks:  # pylint: disable=too-few-public-methods

    def __init__(self,
                 request: Callable[..., requests.models.Response],
                 api: StackExchangeApi):
        self.request = request
        self.api = api
        functools.update_wrapper(self, request)

    # noinspection PyProtectedMember
    def __call__(self,
                 method: str,
                 url: str,
                 *,
                 params: ParametersModel,
                 **kwargs):
        self.api._check_backoff(StackExchangeApi.get_api_name())
        self.api._model_post_init(params)
        while True:
            try:
                self.api._rps_deque.pop()
                break
            except IndexError:
                print("Rate limiting has kicked in at "
                      + f"{self.api._rps} requests per second.")
                time.sleep(1 / self.api._rps)
        if method == HTTPMethod.GET:
            query_params = params.model_dump()
            if params.model_extra:
                query_params |= params.model_extra
            response = self.request(method, url, params=query_params, **kwargs)
        else:
            response = self.request(method, url, json=params, **kwargs)
        StackExchangeApi.check_response(response)
        return response
