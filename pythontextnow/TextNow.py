from __future__ import annotations

import os
from typing import Dict, Generator, List, Optional, Tuple, Union
from dotenv import load_dotenv

from pythontextnow.api.Client import Client
from pythontextnow.api.TextNowAPI import TextNowAPI
from pythontextnow.model.Message import Message
from pythontextnow.model.User import User
from pythontextnow.service.ConversationService import ConversationService
from pythontextnow.util.SessionManager import DEFAULT_USER_AGENT


class TextNow:
    """
    Unified client class for the TextNow API.

    Preferred usage:
        import os
        from dotenv import load_dotenv
        from pythontextnow import TextNow

        load_dotenv()
        username = os.getenv("TEXTNOW_USERNAME")
        sid_cookie = os.getenv("TEXTNOW_SID_COOKIE")

        client = TextNow(username=username, sid_cookie=sid_cookie)
        client.send_sms(to="+12025550143", message="Hello!")

    Static usage (without a class instance):
        # Direct login attempt:
        TextNow.direct_login(username="user@example.com", password="my_password")

        # Extract session from cURL/HAR bundle:
        cookies, ua = TextNow.extract_session(bundle_text, username="user")

        # Keepalive ping:
        TextNow.ping_keepalive(username="user", sid_cookie="s%3A...")
    """

    def __init__(
        self,
        username: Optional[str] = None,
        sid_cookie: Optional[str] = None,
        csrf_cookie: Optional[str] = None,
        user_agent: Optional[str] = None,
        auto_load_env: bool = False,
    ):
        if auto_load_env:
            load_dotenv()
            if not username:
                username = os.environ.get("TEXTNOW_USERNAME")
            if not sid_cookie:
                sid_cookie = os.environ.get("TEXTNOW_SID_COOKIE")
            if not user_agent:
                user_agent = os.environ.get("TEXTNOW_USER_AGENT")

        if not username or not sid_cookie:
            raise ValueError(
                "Missing required credentials: 'username' and 'sid_cookie' must be provided. "
                "Pass them explicitly (e.g., TextNow(username=..., sid_cookie=...)) "
                "or set auto_load_env=True to load them from your environment/.env file."
            )

        self.username: str = username
        self.sid_cookie: str = sid_cookie
        self.user_agent: str = user_agent or DEFAULT_USER_AGENT

        # Configure underlying client state
        Client.set_client_config(
            username=self.username,
            sid_cookie=self.sid_cookie,
            csrf_cookie=csrf_cookie,
            user_agent=self.user_agent,
            auto_load_env=False,
        )
        self.api: TextNowAPI = TextNowAPI()

    # -----------------------------------------------------------------------
    # High-Level Instance API
    # -----------------------------------------------------------------------

    def get_user(self) -> User:
        """Fetch details about the authenticated TextNow account (username, phone number, email)."""
        return self.api.get_user()

    def get_conversation(
        self, phone_number: Union[str, list[str]]
    ) -> ConversationService:
        """
        Return a ConversationService instance for a phone number or list of phone numbers.
        Phone numbers must be in E.164 format (e.g., +1XXXXXXXXXX).
        """
        numbers = [phone_number] if isinstance(phone_number, str) else phone_number
        return ConversationService(conversation_phone_numbers=numbers)

    def send_sms(self, *, to: str, message: str) -> None:
        """
        Send an SMS text message to the specified phone number (E.164 format: +1XXXXXXXXXX).
        """
        conv = self.get_conversation(to)
        conv.send_message(message=message)

    def send_mms(self, *, to: str, file_path: str) -> None:
        """
        Send media (image, video, or GIF) to the specified phone number.
        """
        conv = self.get_conversation(to)
        conv.send_media(file_path=file_path)

    def get_messages(
        self, *, phone_number: str, limit: int = 10
    ) -> list[Message]:
        """
        Fetch the most recent messages from a conversation with the specified phone number.
        Returns a list of Message objects (newest to oldest).
        """
        conv = self.get_conversation(phone_number)
        messages: list[Message] = []
        for batch in conv.get_messages(num_messages=limit):
            messages.extend(batch)
            if len(messages) >= limit:
                break
        return messages[:limit]

    def mark_as_read(self, message: Message) -> None:
        """
        Mark a given Message as read.
        """
        self.api.mark_message_as_read(message=message)

    def delete_message(self, message_id: str) -> None:
        """
        Delete a specific message by its message ID.
        """
        self.api.delete_message(message_id=message_id)

    def keepalive(self, update_env: bool = False, verbose: bool = False) -> bool:
        """
        Send a lightweight keepalive ping (<0.3s) to extend the connect.sid session by another 24 hours.
        """
        return TextNow.ping_keepalive(
            username=self.username,
            sid_cookie=self.sid_cookie,
            user_agent=self.user_agent,
            update_env=update_env,
            verbose=verbose,
        )

    def direct_login_attempt(
        self,
        password: str,
        cookies: Optional[dict] = None,
        update_env: bool = False,
        verbose: bool = True,
    ) -> bool:
        """
        Attempt direct HTTP login using this client's username and the provided password.

        NOTE: Experimental / Advanced. TextNow's login endpoint is protected by PerimeterX
        (HUMAN Security) bot defense, which rejects raw HTTP clients lacking browser telemetry.
        For reliable production use, use extract_and_update_session(...) or extract_from_bundle.py
        with session_keepalive.py.
        """
        return TextNow.direct_login(
            username=self.username,
            password=password,
            cookies=cookies,
            update_env=update_env,
            user_agent=self.user_agent,
            verbose=verbose,
        )

    def extract_and_update_session(
        self, raw_bundle: str, update_env: bool = False, validate: bool = True
    ) -> Tuple[Dict[str, str], Optional[str]]:
        """
        Extract session cookies from a cURL or HAR request bundle and update this client's session.
        """
        cookies, ua = TextNow.extract_session(
            raw_bundle=raw_bundle,
            username=self.username,
            update_env=update_env,
            validate=validate,
        )
        if "connect.sid" in cookies:
            self.sid_cookie = cookies["connect.sid"]
            if ua:
                self.user_agent = ua
            Client.set_client_config(
                username=self.username,
                sid_cookie=self.sid_cookie,
                user_agent=self.user_agent,
                auto_load_env=False,
            )
        return cookies, ua

    # -----------------------------------------------------------------------
    # Static Utility Methods (No Class Instance Required)
    # -----------------------------------------------------------------------

    @staticmethod
    def direct_login(
        username: str,
        password: str,
        cookies: Optional[dict] = None,
        update_env: bool = False,
        user_agent: Optional[str] = None,
        verbose: bool = True,
    ) -> bool:
        """
        Statically attempt direct HTTP login without declaring a TextNow class object.

        NOTE: Experimental / Advanced. Subject to PerimeterX anti-bot challenges on
        https://www.textnow.com/api/sessions. May require passing pre-solved PerimeterX
        cookies (_px3) if running outside of a browser.
        """
        try:
            from tools.direct_http_login import attempt_login
        except ImportError:
            from pythontextnow.tools.direct_http_login import attempt_login

        return attempt_login(
            username=username,
            password=password,
            cookies=cookies,
            update_env=update_env,
            user_agent=user_agent,
            verbose=verbose,
        )

    @staticmethod
    def extract_session(
        raw_bundle: str,
        username: Optional[str] = None,
        update_env: bool = False,
        validate: bool = True,
    ) -> Tuple[Dict[str, str], Optional[str]]:
        """
        Statically extract cookies and user agent from any cURL command or HAR file content.
        """
        try:
            from tools.extract_from_bundle import extract_and_save
        except ImportError:
            from pythontextnow.tools.extract_from_bundle import extract_and_save

        return extract_and_save(
            raw_bundle=raw_bundle,
            username=username,
            update_env=update_env,
            validate=validate,
        )

    @staticmethod
    def ping_keepalive(
        username: Optional[str] = None,
        sid_cookie: Optional[str] = None,
        user_agent: Optional[str] = None,
        update_env: bool = False,
        verbose: bool = True,
    ) -> bool:
        """
        Statically send a 24-hour session renewal ping (<0.3s) without declaring a TextNow object.
        """
        try:
            from tools.session_keepalive import ping_and_extend_session
        except ImportError:
            from pythontextnow.tools.session_keepalive import ping_and_extend_session

        return ping_and_extend_session(
            username=username,
            sid_cookie=sid_cookie,
            user_agent=user_agent,
            update_env=update_env,
            verbose=verbose,
        )
