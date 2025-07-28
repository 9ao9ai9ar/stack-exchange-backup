import datetime
import inspect
import threading
import time
from collections import deque
from collections.abc import Callable, Generator
from http import HTTPMethod
from typing import (
    Any,
    Literal,
    cast,
    overload,
)

import niquests as requests
from pydantic import SecretStr

from stackexchange.model_extend import *

__version__ = "2.3"
__all__ = ["StackExchangeApi"]


# https://stackoverflow.com/q/6760685
# https://gist.github.com/wowkin2/3af15bfbf197a14a2b0b2488a1e8c787
class SingletonMeta(type):
    _instances = {}
    _init = {}

    # noinspection PyUnusedLocal
    def __init__(cls, clsname, bases, dct, **kwds):
        super().__init__(type)
        cls._init[cls] = dct.get("__init__", None)

    def __call__(cls, *args, **kwargs):
        init = cls._init[cls]
        if init is not None:
            bound = inspect.signature(init).bind(None, *args, **kwargs)
            bound.apply_defaults()
            callargs = bound.arguments.items()
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


# pyright: reportPrivateUsage=false
class ProxiedRequest:  # pylint: disable=too-few-public-methods

    def __init__(self,
                 request: Callable[..., requests.models.Response],
                 api: "StackExchangeApi") -> None:
        self.request = request
        self.api = api
        # functools.update_wrapper(self, request)

    # noinspection PyProtectedMember
    def __call__(self,
                 /,
                 method: str,
                 url: str,
                 *,
                 params: ParametersModel,
                 **kwargs) -> requests.models.Response:
        self.api._check_backoff(StackExchangeApi.get_api_name())
        self.api._add_auth(params)
        while True:
            try:
                self.api._limit_rate_deque.pop()
                break
            except IndexError:
                print("Rate limiting has kicked in at "
                      + f"{self.api._limit_rate} requests per second.")
                time.sleep(1 / self.api._limit_rate)
        match method:
            case HTTPMethod.GET:
                kwargs.update({"params": params.model_dump()})
                response = self.request(method, url, **kwargs)
            case _:
                kwargs.update({"data": params.model_dump()})
                response = self.request(method, url, **kwargs)
        StackExchangeApi.check_response(response)
        return response


# pylint: disable=too-many-instance-attributes
class StackExchangeApi(metaclass=SingletonMeta):
    API_ROOT = f"https://api.stackexchange.com/{__version__}"
    API_KEY = "YLTVFmHkeJbm7ZIOoXstag(("
    MAX_REQUESTS_PER_SECOND = 30
    """If a single IP is making more than 30 requests a second, new 
    requests will be dropped.
    """
    MAX_CONCURRENT_REQUESTS = 1
    """Just being conservative here, as the exact rate limit mechanisms 
    are not well-understood.
    """
    MAX_PAGE_SIZE = 100

    def __init__(self,
                 api_key=API_KEY,
                 access_token=None,
                 limit_rate=MAX_REQUESTS_PER_SECOND) -> None:
        self._api_key: str | None = api_key
        """API keys, also known as request keys or app keys,
        grant more requests per day (10,000 vs 300 for anonymous API 
        access) and allow querying results past page 25.
        """
        self._access_token: SecretStr | None = access_token
        self._limit_rate: int = limit_rate
        self._limit_rate_deque: deque[int] = deque(
            [0] * StackExchangeApi.MAX_CONCURRENT_REQUESTS,
            maxlen=StackExchangeApi.MAX_CONCURRENT_REQUESTS,
        )
        self._limit_rate_timer \
            = threading.Thread(target=self._refill_limit_rate_deque,
                               name="Thread-Limit-Rate-Timer",
                               daemon=True)
        self._limit_rate_timer.start()
        self._backoff: dict[str, int] = {}
        self._quota_remaining: int | None = None
        """
        `Documentation <https://api.stackexchange.com/docs/throttle>`_:
        A dynamic throttle is also in place on a per-method level.
        If an application receives a response with the backoff field 
        set, it must wait that many seconds before hitting the same 
        method again.
        All methods (even seemingly trivial ones) may return backoff.
        """
        self.session = requests.Session()
        # Can't be arsed to wade through the rigmarole of
        # trying to please the Python type checkers.
        self.session.request = ProxiedRequest(
            self.session.request,
            self,
        )  # pyright: ignore [reportAttributeAccessIssue]

    def _refill_limit_rate_deque(self) -> None:
        while True:
            time.sleep(1 / self._limit_rate)
            self._limit_rate_deque.appendleft(0)

    @classmethod
    def get_api_name(cls) -> str:
        current_frame = inspect.currentframe()
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
            return "unknown"
        else:
            return current_frame.f_code.co_name

    def _check_backoff(self, api_name: str) -> None:
        if self._backoff.get(api_name) is not None:
            now_timestamp = datetime.datetime.now(datetime.UTC).timestamp()
            backoff_timestamp = self._backoff.pop(api_name)
            # Add 1 more second just to be safe
            wait_seconds = round(backoff_timestamp - now_timestamp + 1)
            if wait_seconds > 0:
                print(
                    "We've made too many requests to the Stack Exchange API, "
                    + f"so we will need to wait for {wait_seconds} seconds. "
                    + "Please be patient...",
                    flush=True,
                )
                time.sleep(wait_seconds)

    def _add_auth(self, params: ParametersModel) -> None:
        if params.auth is None:
            params.auth = Auth(key=self._api_key,
                               access_token=self._access_token)

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

    def _parse_response[T](self,
                           response: requests.models.Response,
                           model: type[T]) -> Response[T]:
        # noinspection PyTypeHints
        parsed = (Response[model]
                  .model_validate_json(response.content or bytes()))
        self._update_backoff(StackExchangeApi.get_api_name(), parsed)
        self.check_quota_remaining(parsed)
        return parsed

    def check_quota_remaining(self, response: Response) -> None:
        if (quota_remaining := response.quota_remaining) is not None:
            self._quota_remaining = quota_remaining
            if self._quota_remaining <= 0:
                print("We've reached the daily usage quota. "
                      + "The program will resume from sleep in 24 hours "
                      + "(press Ctrl+C to abort the pending operation).",
                      flush=True)
                time.sleep(24 * 60 * 60)

    def _update_backoff(self, api_name: str, response: Response) -> None:
        if response.backoff:
            self._backoff[api_name] \
                = round(datetime.datetime.now(datetime.UTC).timestamp()
                        + response.backoff)

    @overload
    # pylint: disable=too-many-arguments
    def _call_api[T](self,
                     /,
                     url_template: str,
                     params: ParametersModel,
                     model: type[T],
                     *,
                     auto_pagination: bool = ...,
                     items_only: Literal[False],
                     http_method: HTTPMethod = ...) \
            -> Generator[Response[T], None, None]:
        ...

    @overload
    # pylint: disable=too-many-arguments
    def _call_api[T](self,
                     /,
                     url_template: str,
                     params: ParametersModel,
                     model: type[T],
                     *,
                     auto_pagination: bool = ...,
                     items_only: Literal[True] = ...,
                     http_method: HTTPMethod = ...) \
            -> Generator[T, None, None]:
        ...

    # pylint: disable=too-many-arguments, too-many-locals
    def _call_api[T](self,
                     /,
                     url_template: str,
                     params: ParametersModel,
                     model: type[T],
                     *,
                     auto_pagination=True,
                     items_only=True,
                     http_method=HTTPMethod.GET) \
            -> Generator[Response[T] | T, None, None]:
        path_parameter_ids_varname = None
        path_parameter_ids_batch = [None]
        path_parameters = {}
        for k, v in type(params).model_fields.items():
            if v.exclude and (field := getattr(params, k, None)) is not None:
                if isinstance(field, list):
                    path_parameter_ids_varname = k
                    path_parameter_ids_batch = getattr(params, k)
                else:
                    path_parameters[k] = getattr(params, k)
        for ids in path_parameter_ids_batch:
            if path_parameter_ids_varname:
                path_parameters.update({path_parameter_ids_varname: ids})
            url = url_template.format(**path_parameters)
            page = 0
            has_more = True
            while has_more:
                page += 1
                if auto_pagination:
                    setattr(params,
                            "paging",
                            Paging(page=page,
                                   pagesize=StackExchangeApi.MAX_PAGE_SIZE))
                response = (self.session
                            .request(http_method, url,
                                     params=cast(dict, params)))
                parsed = self._parse_response(response, model)
                has_more = ((parsed.has_more or parsed.items)
                            and auto_pagination)
                if items_only:
                    yield from parsed.items or []
                else:
                    yield parsed

    @overload
    def questions_by_ids(self,
                         /,
                         params: QuestionsByIdsParameters,
                         *,
                         items_only: Literal[False]) \
            -> Generator[Response[Question], None, None]:
        ...

    @overload
    def questions_by_ids(self,
                         /,
                         params: QuestionsByIdsParameters,
                         *,
                         items_only: Literal[True] = ...) \
            -> Generator[Question, None, None]:
        ...

    def questions_by_ids(self,
                         /,
                         params: QuestionsByIdsParameters,
                         *,
                         items_only=True) \
            -> Generator[Response[Question] | Question, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/questions-by-ids>`_
        Returns the questions identified in {ids}.

        :param params:
        :param items_only:
        :return:
        """
        # noinspection PyTypeChecker
        return self._call_api(
            StackExchangeApi.API_ROOT + "/questions/{ids}",
            params,
            Question,
            auto_pagination=True,
            items_only=items_only,
        )

    @overload
    def answers_on_users(self,
                         /,
                         params: AnswersOnUsersParameters,
                         *,
                         auto_pagination: bool = ...,
                         items_only: Literal[False]) \
            -> Generator[Response[Answer], None, None]:
        ...

    @overload
    def answers_on_users(self,
                         /,
                         params: AnswersOnUsersParameters,
                         *,
                         auto_pagination: bool = ...,
                         items_only: Literal[True] = ...) \
            -> Generator[Answer, None, None]:
        ...

    def answers_on_users(self,
                         /,
                         params: AnswersOnUsersParameters,
                         *,
                         auto_pagination=True,
                         items_only=True) \
            -> Generator[Response[Answer] | Answer, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/answers-on-users>`_
        Returns the answers the users in {ids} have posted.

        :param params:
        :param auto_pagination:
        :param items_only:
        :return:
        """
        # noinspection PyTypeChecker
        return self._call_api(
            StackExchangeApi.API_ROOT + "/users/{ids}/answers",
            params,
            Answer,
            auto_pagination=auto_pagination,
            items_only=items_only,
        )

    @overload
    def questions_on_users(self,
                           /,
                           params: QuestionsOnUsersParameters,
                           *,
                           auto_pagination: bool = ...,
                           items_only: Literal[False]) \
            -> Generator[Response[Question], None, None]:
        ...

    @overload
    def questions_on_users(self,
                           /,
                           params: QuestionsOnUsersParameters,
                           *,
                           auto_pagination: bool = ...,
                           items_only: Literal[True] = ...) \
            -> Generator[Question, None, None]:
        ...

    def questions_on_users(self,
                           /,
                           params: QuestionsOnUsersParameters,
                           *,
                           auto_pagination=True,
                           items_only=True) \
            -> Generator[Response[Question] | Question, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/questions-on-users>`_
        Gets the questions asked by the users in {ids}.

        :param params:
        :param auto_pagination:
        :param items_only:
        :return:
        """
        # noinspection PyTypeChecker
        return self._call_api(
            StackExchangeApi.API_ROOT + "/users/{ids}/questions",
            params,
            Question,
            auto_pagination=auto_pagination,
            items_only=items_only,
        )

    def simulate_error(self, /, params: SimulateErrorParameters) \
            -> Response[Any]:
        """`Documentation <https://api.stackexchange.com/docs/simulate-error>`_
        This method allows you to generate an error.

        :param params:
        :return:
        """
        return next(
            self._call_api(
                StackExchangeApi.API_ROOT + "/errors/{id}",
                params,
                Error,
                auto_pagination=False,
                items_only=False
            )
        )

    @overload
    def create_filter(self,
                      /,
                      params: CreateFilterParameters,
                      *,
                      items_only: Literal[False],
                      http_method: Literal[HTTPMethod.GET]
                                   | Literal[HTTPMethod.POST] = ...) \
            -> Response[Filter]:
        ...

    @overload
    def create_filter(self,
                      /,
                      params: CreateFilterParameters,
                      *,
                      items_only: Literal[True] = ...,
                      http_method: Literal[HTTPMethod.GET]
                                   | Literal[HTTPMethod.POST] = ...) \
            -> Filter:
        ...

    def create_filter(self,
                      /,
                      params: CreateFilterParameters,
                      *,
                      items_only=True,
                      http_method=HTTPMethod.GET) \
            -> Response[Filter] | Filter:
        """`Documentation <https://api.stackexchange.com/docs/create-filter>`_
        Creates a new filter given a list of includes, excludes, a base
        filter, and whether or not this filter should be "unsafe".

        When building filters, refer to the fields of the
        common wrapper object with a leading "."

        :param params:
        :param items_only:
        :param http_method:
        :return:
        """
        # noinspection PyTypeChecker
        return next(
            self._call_api(
                StackExchangeApi.API_ROOT + "/filters/create",
                params,
                Filter,
                auto_pagination=False,
                items_only=items_only,
                http_method=http_method,
            )
        )

    @overload
    def read_filter(self,
                    /,
                    params: ReadFilterParameters,
                    *,
                    items_only: Literal[False]) \
            -> Generator[Response[Filter], None, None]:
        ...

    @overload
    def read_filter(self,
                    /,
                    params: ReadFilterParameters,
                    *,
                    items_only: Literal[True] = ...) \
            -> Generator[Filter, None, None]:
        ...

    def read_filter(self,
                    /,
                    params: ReadFilterParameters,
                    *,
                    items_only=True) \
            -> Generator[Response[Filter] | Filter, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/read-filter>`_
        Returns the fields included by the given filters,
        and the "safeness" of those filters.

        :param params:
        :param items_only:
        :return:
        """
        # noinspection PyTypeChecker
        return self._call_api(
            StackExchangeApi.API_ROOT + "/filters/{filters}",
            params,
            Filter,
            auto_pagination=True,
            items_only=items_only,
        )

    @overload
    def sites(self,
              /,
              params: SitesParameters,
              *,
              auto_pagination: bool = ...,
              items_only: Literal[False]) \
            -> Generator[Response[Site], None, None]:
        ...

    @overload
    def sites(self,
              /,
              params: SitesParameters,
              *,
              auto_pagination: bool = ...,
              items_only: Literal[True] = ...) \
            -> Generator[Site, None, None]:
        ...

    def sites(self,
              /,
              params: SitesParameters,
              *,
              auto_pagination=True,
              items_only=True) \
            -> Generator[Response[Site] | Site, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/sites>`_
        Returns all sites in the network.

        :param params:
        :param auto_pagination:
        :param items_only:
        :return:
        """
        # noinspection PyTypeChecker
        return self._call_api(
            StackExchangeApi.API_ROOT + "/sites",
            params,
            Site,
            auto_pagination=auto_pagination,
            items_only=items_only,
        )

    @overload
    def associated_users(self,
                         /,
                         params: AssociatedUsersParameters,
                         *,
                         auto_pagination: bool = ...,
                         items_only: Literal[False]) \
            -> Generator[Response[NetworkUser], None, None]:
        ...

    @overload
    def associated_users(self,
                         /,
                         params: AssociatedUsersParameters,
                         *,
                         auto_pagination: bool = ...,
                         items_only: Literal[True] = ...) \
            -> Generator[NetworkUser, None, None]:
        ...

    def associated_users(self,
                         /,
                         params: AssociatedUsersParameters,
                         *,
                         auto_pagination=True,
                         items_only=True) \
            -> Generator[Response[NetworkUser] | NetworkUser, None, None]:
        """`Documentation <https://api.stackexchange.com/docs/associated-users>`_
        Returns all of a user's associated accounts,
        given their account_ids in {ids}.
        It is a `known bug <https://stackapps.com/q/8666/>`_ that
        results are not returned for meta sites.

        :param params:
        :param auto_pagination:
        :param items_only:
        :return:
        """
        # noinspection PyTypeChecker
        return self._call_api(
            StackExchangeApi.API_ROOT + "/users/{ids}/associated",
            params,
            NetworkUser,
            auto_pagination=auto_pagination,
            items_only=items_only,
        )
