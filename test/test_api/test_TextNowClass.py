import datetime
import os
from unittest import TestCase, mock

from pythontextnow import TextNow
from pythontextnow.enum import MessageDirection, MessageType
from pythontextnow.model.TextMessage import TextMessage
from pythontextnow.model.User import User
from test.helper.helper_classes import MockResponse


class TestTextNowClass(TestCase):
    PATH_TO_DATA_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../data")
    )

    @classmethod
    @mock.patch("requests.get")
    def setUpClass(cls, mock_requests_get):
        with open(os.path.join(cls.PATH_TO_DATA_DIR, "dummy_messaging_page.html")) as f:
            dummy_messaging_page_str = f.read()

        mock_response = MockResponse(dict(), 200, text=dummy_messaging_page_str)
        mock_requests_get.return_value = mock_response

    def test_init_missing_credentials_raises_error(self):
        with self.assertRaises(ValueError):
            TextNow(username=None, sid_cookie=None, auto_load_env=False)

    @mock.patch("requests.get")
    def test_init_explicit_credentials(self, mock_requests_get):
        mock_requests_get.return_value = MockResponse(dict(), 200, text="")
        client = TextNow(
            username="test_user",
            sid_cookie="test_sid",
            auto_load_env=False,
        )
        self.assertEqual("test_user", client.username)
        self.assertEqual("test_sid", client.sid_cookie)

    @mock.patch.dict(
        os.environ, {"TEXTNOW_USERNAME": "env_user", "TEXTNOW_SID_COOKIE": "env_sid"}
    )
    @mock.patch("requests.get")
    def test_init_auto_load_env(self, mock_requests_get):
        mock_requests_get.return_value = MockResponse(dict(), 200, text="")
        client = TextNow(auto_load_env=True)
        self.assertEqual("env_user", client.username)
        self.assertEqual("env_sid", client.sid_cookie)

    @mock.patch("requests.request")
    @mock.patch("requests.get")
    def test_get_user(self, mock_requests_get, mock_requests_request):
        mock_requests_get.return_value = MockResponse(dict(), 200, text="")
        dummy_user = {
            "user_id": 123,
            "username": "test_user",
            "email": "test@example.com",
            "phone_number": "15551234567",
        }
        mock_requests_request.return_value = MockResponse(dummy_user, 200)

        client = TextNow(
            username="test_user", sid_cookie="test_sid", auto_load_env=False
        )
        user = client.get_user()

        self.assertIsInstance(user, User)
        self.assertEqual("test_user", user.username)
        self.assertEqual("15551234567", user.phone_number)

    @mock.patch("requests.request")
    @mock.patch("requests.get")
    def test_send_sms(self, mock_requests_get, mock_requests_request):
        mock_requests_get.return_value = MockResponse(dict(), 200, text="")
        mock_requests_request.return_value = MockResponse(dict(), 200)

        client = TextNow(
            username="test_user", sid_cookie="test_sid", auto_load_env=False
        )
        client.send_sms(to="+12025550143", message="Hello world!")

        self.assertTrue(mock_requests_request.called)

    @mock.patch("requests.request")
    @mock.patch("requests.get")
    def test_get_messages(self, mock_requests_get, mock_requests_request):
        mock_requests_get.return_value = MockResponse(dict(), 200, text="")
        mock_message = {
            "id": "msg_123",
            "username": "test_user",
            "contact_value": "+12025550143",
            "message_direction": 1,
            "message_type": 1,
            "message": "Hello there",
            "read": True,
            "date": "2026-01-01T00:00:00Z",
            "conversation_filtering": {"first_time_contact": False},
        }
        mock_requests_request.return_value = MockResponse(
            {"messages": [mock_message]}, 200
        )

        client = TextNow(
            username="test_user", sid_cookie="test_sid", auto_load_env=False
        )
        messages = client.get_messages(phone_number="+12025550143", limit=1)

        self.assertEqual(1, len(messages))
        self.assertIsInstance(messages[0], TextMessage)
        self.assertEqual("Hello there", messages[0].text)

    @mock.patch("requests.request")
    @mock.patch("requests.get")
    def test_delete_message(self, mock_requests_get, mock_requests_request):
        mock_requests_get.return_value = MockResponse(dict(), 200, text="")
        mock_requests_request.return_value = MockResponse(dict(), 200)

        client = TextNow(
            username="test_user", sid_cookie="test_sid", auto_load_env=False
        )
        client.delete_message(message_id="msg_123")

        self.assertTrue(mock_requests_request.called)

    @mock.patch("tools.direct_http_login.attempt_login")
    def test_static_direct_login(self, mock_attempt_login):
        mock_attempt_login.return_value = True
        success = TextNow.direct_login("user@test.com", "password123", verbose=False)
        self.assertTrue(success)
        mock_attempt_login.assert_called_once_with(
            username="user@test.com",
            password="password123",
            cookies=None,
            update_env=False,
            user_agent=None,
            verbose=False,
        )

    def test_static_extract_session(self):
        sample_bundle = "Cookie: connect.sid=s%3Atest_extracted_sid; _csrf=test_csrf;"
        cookies, ua = TextNow.extract_session(sample_bundle, validate=False)
        self.assertIn("connect.sid", cookies)
        self.assertEqual("s%3Atest_extracted_sid", cookies["connect.sid"])

    @mock.patch("tools.session_keepalive.ping_and_extend_session")
    def test_static_ping_keepalive(self, mock_ping):
        mock_ping.return_value = True
        result = TextNow.ping_keepalive(
            username="user", sid_cookie="sid123", verbose=False
        )
        self.assertTrue(result)
        mock_ping.assert_called_once_with(
            username="user",
            sid_cookie="sid123",
            user_agent=None,
            update_env=False,
            verbose=False,
        )

    @mock.patch("requests.get")
    @mock.patch("tools.session_keepalive.ping_and_extend_session")
    def test_instance_keepalive(self, mock_ping, mock_requests_get):
        mock_requests_get.return_value = MockResponse(dict(), 200, text="")
        mock_ping.return_value = True

        client = TextNow(username="my_user", sid_cookie="my_sid", auto_load_env=False)
        result = client.keepalive(verbose=False)
        self.assertTrue(result)
        mock_ping.assert_called_once_with(
            username="my_user",
            sid_cookie="my_sid",
            user_agent=client.user_agent,
            update_env=False,
            verbose=False,
        )
