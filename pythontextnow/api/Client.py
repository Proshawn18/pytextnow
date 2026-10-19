from __future__ import annotations

import datetime
import os
from dataclasses import dataclass, field
from typing import Optional, Union

from pythontextnow.util.SessionManager import DEFAULT_USER_AGENT, SessionManager


@dataclass
class ClientConfig:
    """
    Used to hold the Client config.
    """

    username: str
    headers: dict
    cookies: dict
    last_call_time: datetime.datetime = field(default_factory=datetime.datetime.now)
    sid_cookie: Optional[str] = None
    user_agent: str = DEFAULT_USER_AGENT


class Client:
    """
    This class is used to store and set up initial Client configuration.
    """

    client_config: Optional[ClientConfig] = None

    @classmethod
    def set_client_config(
        cls,
        *,
        username: Optional[str] = None,
        sid_cookie: Optional[str] = None,
        csrf_cookie: Optional[str] = None,
        cookies: Optional[Union[dict, str]] = None,
        user_agent: Optional[str] = None,
        auto_load_env: bool = False,
    ) -> None:
        user = username
        sid = sid_cookie
        ua = user_agent

        if auto_load_env:
            user = user or os.environ.get("TEXTNOW_USERNAME")
            sid = sid or os.environ.get("TEXTNOW_SID_COOKIE")
            ua = ua or os.environ.get("TEXTNOW_USER_AGENT")

        if not user or not sid:
            raise ValueError(
                "Both 'username' and 'sid_cookie' must be provided. "
                "Pass them explicitly or set auto_load_env=True."
            )
        ua = ua or DEFAULT_USER_AGENT

        # Load any existing cached session cookies
        session_cookies = SessionManager.load_session(user)

        # Merge provided sid_cookie
        session_cookies["connect.sid"] = sid

        # Merge additional cookies if provided
        if cookies:
            if isinstance(cookies, str):
                cookies = SessionManager.parse_cookie_string(cookies)
            session_cookies.update(cookies)

        # Merge csrf_cookie if provided
        if csrf_cookie:
            session_cookies["_csrf"] = csrf_cookie
            session_cookies["XSRF-TOKEN"] = csrf_cookie

        # If XSRF-TOKEN is missing, fetch fresh CSRF token from messaging page
        if "XSRF-TOKEN" not in session_cookies:
            fetched_cookies, xsrf = SessionManager.fetch_csrf_tokens(sid, ua)
            session_cookies.update(fetched_cookies)
            if xsrf:
                session_cookies["XSRF-TOKEN"] = xsrf

        xsrf_token = session_cookies.get("XSRF-TOKEN") or session_cookies.get("_csrf", "")

        headers = {
            "user-agent": ua,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Origin": "https://www.textnow.com",
            "Referer": "https://www.textnow.com/messaging",
            "x-requested-with": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        if xsrf_token:
            headers["x-xsrf-token"] = xsrf_token
            headers["x-csrf-token"] = xsrf_token

        # Save session for persistence
        SessionManager.save_session(user, session_cookies, ua)

        client_config = ClientConfig(
            username=user,
            headers=headers,
            cookies=session_cookies,
            last_call_time=datetime.datetime.now(),
            sid_cookie=sid,
            user_agent=ua,
        )
        cls.client_config = client_config

    @classmethod
    def get_client_config(cls) -> ClientConfig:
        if cls.client_config is None:
            raise RuntimeError(
                "Client configuration is not set. Please call Client.set_client_config(...) first."
            )
        return cls.client_config

    @classmethod
    def update(cls, **kwargs) -> None:
        if cls.client_config is None:
            return
        new_last_call_time = kwargs.pop("last_call_time", None)
        if new_last_call_time is not None:
            cls.client_config.last_call_time = new_last_call_time
        if "cookies" in kwargs:
            cls.client_config.cookies.update(kwargs["cookies"])
            SessionManager.save_session(
                cls.client_config.username,
                cls.client_config.cookies,
                cls.client_config.user_agent,
            )
        if "headers" in kwargs:
            cls.client_config.headers.update(kwargs["headers"])
