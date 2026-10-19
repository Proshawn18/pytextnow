import json
import urllib
from datetime import datetime
from typing import Optional
from urllib import parse
from urllib.parse import quote

import requests

from pythontextnow.api.Client import Client, ClientConfig
from pythontextnow.decorator.cooldown import enforce_cooldown
from pythontextnow.enum import ContactType, MessageDirection, MessageType, ReadStatus
from pythontextnow.model.Group import Group
from pythontextnow.model.Message import Message
from pythontextnow.model.MultiMediaMessage import MultiMediaMessage
from pythontextnow.model.TextMessage import TextMessage
from pythontextnow.model.User import User
from pythontextnow.util.ConfigReader import ConfigReader
from pythontextnow.util.SessionManager import SessionManager


class TextNowAPI:
    def __init__(self):
        self.__BASE_URL = ConfigReader.get("api", "textnow_base_url")
        self.__VERSION = ConfigReader.get("api", "version")
        self.__API_ROUTE = ConfigReader.get("api", "api_route")
        self.__ATTACHMENT_URL_ROUTE = ConfigReader.get("api", "attachment_url_route")
        self.__CONVERSATIONS_ROUTE = ConfigReader.get("api", "conversations_route")
        self.__GROUPS_ROUTE = ConfigReader.get("api", "groups_route")
        self.__MESSAGES_ROUTE = ConfigReader.get("api", "messages_route")
        self.__MESSAGING_ROUTE = ConfigReader.get("api", "messaging_route")
        self.__SEND_ATTACHMENT_ROUTE = ConfigReader.get("api", "send_attachment_route")
        self.__USERS_ROUTE = ConfigReader.get("api", "users_route")

        self.__MAX_MESSAGE_RESPONSE_SIZE = 30

    @property
    def __client_config(self) -> ClientConfig:
        return Client.get_client_config()

    def _prepare_request_kwargs(self, **kwargs) -> dict:
        config = self.__client_config
        headers = dict(config.headers)
        if "headers" in kwargs and kwargs["headers"]:
            headers.update(kwargs["headers"])

        cookies = dict(config.cookies)
        if "cookies" in kwargs and kwargs["cookies"]:
            cookies.update(kwargs["cookies"])

        xsrf = cookies.get("XSRF-TOKEN") or cookies.get("_csrf")
        if xsrf:
            headers["x-xsrf-token"] = xsrf
            headers["x-csrf-token"] = xsrf

        if "Origin" not in headers:
            headers["Origin"] = self.__BASE_URL
        if "Referer" not in headers:
            headers["Referer"] = f"{self.__BASE_URL}/messaging"
        if "x-requested-with" not in headers:
            headers["x-requested-with"] = "XMLHttpRequest"

        kwargs["headers"] = headers
        kwargs["cookies"] = cookies
        return kwargs

    def _execute_request(self, method: str, url: str, **kwargs) -> requests.Response:
        req_kwargs = self._prepare_request_kwargs(**kwargs)
        response = requests.request(method, url, **req_kwargs)

        # Update cookies from response if any Set-Cookie headers are returned
        if hasattr(response, "cookies") and response.cookies:
            new_cookies = dict(response.cookies)
            Client.update(cookies=new_cookies)

        # Handle 403 CSRF token expiration
        if response.status_code == 403:
            try:
                err_data = response.json()
                if err_data.get("error_code") == "INVALID_CSRF_TOKEN":
                    sid = self.__client_config.cookies.get("connect.sid", "")
                    fetched_cookies, new_xsrf = SessionManager.fetch_csrf_tokens(
                        sid, self.__client_config.user_agent
                    )
                    if fetched_cookies:
                        Client.update(cookies=fetched_cookies)
                        req_kwargs = self._prepare_request_kwargs(**kwargs)
                        response = requests.request(method, url, **req_kwargs)
            except Exception:
                pass

        return response

    @enforce_cooldown
    def send_message(self, *, message: str, send_to: str) -> None:
        contact_value = send_to if send_to.startswith("+") else f"+{send_to}"
        json_data = {
            "from_name": self.__client_config.username,
            "has_video": False,
            "reactions": [],
            "reactionData": None,
            "contact_value": contact_value,
            "message": message,
            "read": ReadStatus.READ.value,
            "message_direction": MessageDirection.OUTGOING.value,
            "message_type": MessageType.TEXT.value,
            "new": True,
            "date": datetime.now().isoformat(),
        }

        data = {"json": json.dumps(json_data)}
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

        url = f"{self.__BASE_URL}{self.__API_ROUTE}{self.__USERS_ROUTE}/{self.__client_config.username}{self.__MESSAGES_ROUTE}"
        response = self._execute_request("POST", url, headers=headers, data=data)
        response.raise_for_status()

    @enforce_cooldown
    def get_messages(
        self,
        conversation_phone_number: str,
        *,
        start_message_id: Optional[str] = None,
        page_size: Optional[int],
        get_archived: Optional[bool],
    ) -> list[Message]:
        """
        This gets messages from the conversation with the given phone number.

        This will get all messages before (but not including) the message with the given start_message_id.
        If the given page_size is greater than the max allowed (30), will default to 30.
        """
        page_size = (
            page_size
            if page_size <= self.__MAX_MESSAGE_RESPONSE_SIZE
            else self.__MAX_MESSAGE_RESPONSE_SIZE
        )
        contact_value = (
            f"+{conversation_phone_number}"
            if not conversation_phone_number.startswith("+")
            else conversation_phone_number
        )
        params = {
            "contact_value": contact_value,
            "direction": "past",
            "page_size": page_size,
            "get_archived": 1 if get_archived else 0,
        }
        if start_message_id is not None:
            params["start_message_id"] = start_message_id
        base_url = f"{self.__BASE_URL}{self.__API_ROUTE}{self.__USERS_ROUTE}/{self.__client_config.username}{self.__MESSAGES_ROUTE}"
        url_with_params = f"{base_url}?{urllib.parse.urlencode(params)}"

        response = self._execute_request("GET", url_with_params)
        response.raise_for_status()

        message_dicts = response.json()["messages"]

        all_messages = list()
        # sort into Text and MultiMedia messages
        for message_dict in message_dicts:
            message_type = MessageType.from_value(message_dict["message_type"])
            if message_type == MessageType.TEXT:
                all_messages.append(TextMessage.from_dict(message_dict))
            elif message_type in (MessageType.IMAGE, MessageType.VIDEO):
                all_messages.append(MultiMediaMessage.from_dict(message_dict))
        return all_messages

    @enforce_cooldown
    def mark_message_as_read(self, message: Message) -> None:
        clean_number = quote(message.number)
        url = f"{self.__BASE_URL}{self.__API_ROUTE}{self.__USERS_ROUTE}/{self.__client_config.username}{self.__CONVERSATIONS_ROUTE}/{clean_number}"

        params = {"latest_message_id": message.id_, "http_method": "PATCH"}
        data = {"read": True}

        response = self._execute_request("PATCH", url, params=params, data=data)
        response.raise_for_status()

    @enforce_cooldown
    def delete_message(self, *, message_id: str) -> None:
        """
        Deletes the message with the given ID.
        """
        url = f"{self.__BASE_URL}{self.__API_ROUTE}{self.__USERS_ROUTE}/{self.__client_config.username}{self.__MESSAGES_ROUTE}/{message_id}"
        response = self._execute_request("DELETE", url)
        response.raise_for_status()

    @enforce_cooldown
    def get_attachment_url(self, *, message_type: MessageType) -> str:
        """
        Gets the URL that a file can be uploaded to.
        """
        url = f"{self.__BASE_URL}{self.__API_ROUTE}/{self.__VERSION}{self.__ATTACHMENT_URL_ROUTE}"
        params = {"message_type": message_type.value}
        url_with_params = f"{url}?{parse.urlencode(params)}"

        response = self._execute_request("GET", url_with_params)
        response.raise_for_status()

        return response.json()["result"]

    @enforce_cooldown
    def upload_raw_media(
        self, *, attachment_url: str, raw_media: bytes, media_type: str
    ) -> None:
        """
        Uploads the given raw_media to the given URL.
        """
        headers = {
            "accept": "*/*",
            "content-type": media_type,
            "accept-language": "en-US,en;q=0.9",
            "mode": "cors",
            "method": "PUT",
            "credentials": "omit",
        }

        response = requests.put(
            attachment_url,
            data=raw_media,
            headers=headers,
            cookies=self.__client_config.cookies,
        )
        response.raise_for_status()

    @enforce_cooldown
    def send_attachment(
        self,
        *,
        conversation_phone_number: str,
        message_type: MessageType,
        file_type: str,
        is_video: bool,
        attachment_url: str,
    ) -> None:
        data = {
            "contact_value": conversation_phone_number,
            "contact_type": ContactType.ALTERNATE.value,
            "read": 1,
            "message_direction": MessageDirection.OUTGOING.value,
            "message_type": message_type.value,
            "from_name": self.__client_config.username,
            "has_video": is_video,
            "new": True,
            "date": datetime.now().isoformat(),
            "attachment_url": attachment_url,
            "media_type": file_type,
        }

        url = f"{self.__BASE_URL}{self.__API_ROUTE}/{self.__VERSION}{self.__SEND_ATTACHMENT_ROUTE}"
        response = self._execute_request("POST", url, data=data)
        response.raise_for_status()

    @enforce_cooldown
    def get_groups(self) -> list[Group]:
        url = f"{self.__BASE_URL}{self.__API_ROUTE}{self.__USERS_ROUTE}/{self.__client_config.username}{self.__GROUPS_ROUTE}"
        response = self._execute_request("GET", url)
        response.raise_for_status()

        group_list = list()
        for group_dict in response.json():
            group_list.append(Group.from_dict(group_dict))
        return group_list

    @enforce_cooldown
    def get_user(self) -> User:
        url = f"{self.__BASE_URL}{self.__API_ROUTE}{self.__USERS_ROUTE}/{self.__client_config.username}"
        response = self._execute_request("GET", url)
        response.raise_for_status()

        return User.from_dict(response.json())

    @enforce_cooldown
    def create_group(self, *, phone_numbers: list[str]) -> Group:
        """
        Creates a group with all given phone_numbers and returns it.
        """
        url = f"{self.__BASE_URL}{self.__API_ROUTE}{self.__USERS_ROUTE}/{self.__client_config.username}{self.__GROUPS_ROUTE}"

        data = {"json": {"members": list()}}
        for phone_number in phone_numbers:
            member = {
                "contact_value": phone_number,
                "contact_type": ContactType.ALTERNATE.value,
            }
            data["json"]["members"].append(member)

        data = parse.urlencode(data, quote_via=urllib.parse.quote)
        data = data.replace("%27", "%22")

        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        response = self._execute_request("POST", url, data=data, headers=headers)
        response.raise_for_status()

        return Group.from_dict(response.json())

    @enforce_cooldown
    def delete_conversation(self, *, conversation_phone_number: str) -> None:
        """
        Deletes the conversation with the given phone number.
        """
        conversation_phone_number = (
            conversation_phone_number
            if not conversation_phone_number.startswith("+")
            else conversation_phone_number[1:]
        )
        url = f"{self.__BASE_URL}{self.__API_ROUTE}{self.__USERS_ROUTE}/{self.__client_config.username}{self.__CONVERSATIONS_ROUTE}/%2B{conversation_phone_number}"
        response = self._execute_request("DELETE", url)
        response.raise_for_status()
