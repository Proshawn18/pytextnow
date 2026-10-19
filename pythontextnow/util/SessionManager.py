import json
import os
from pathlib import Path
from typing import Optional, Tuple

import requests

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

SESSION_DIR = Path.home() / ".pythontextnow"


class SessionManager:
    @staticmethod
    def get_session_file(username: str) -> Optional[Path]:
        try:
            SESSION_DIR.mkdir(parents=True, exist_ok=True)
            return SESSION_DIR / f"session_{username}.json"
        except Exception:
            return None

    @staticmethod
    def parse_cookie_string(cookie_str: str) -> dict:
        cookies = {}
        for item in cookie_str.split(";"):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                key, val = item.split("=", 1)
                cookies[key.strip()] = val.strip()
        return cookies

    @classmethod
    def load_session(cls, username: str) -> dict:
        try:
            session_file = cls.get_session_file(username)
            cwd_file = Path.cwd() / f".textnow_session_{username}.json"

            target = (
                session_file
                if session_file and session_file.exists()
                else (cwd_file if cwd_file.exists() else None)
            )
            if target and target.exists():
                with open(target, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("cookies", {})
        except Exception:
            pass
        return {}

    @classmethod
    def save_session(
        cls, username: str, cookies: dict, user_agent: Optional[str] = None
    ) -> None:
        if not cookies:
            return
        data = {
            "username": username,
            "cookies": cookies,
            "user_agent": user_agent or DEFAULT_USER_AGENT,
        }
        # Save to ~/.pythontextnow
        try:
            session_file = cls.get_session_file(username)
            if session_file:
                with open(session_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
        except Exception:
            pass

    @classmethod
    def fetch_csrf_tokens(
        cls, sid_cookie: str, user_agent: Optional[str] = None
    ) -> Tuple[dict, Optional[str]]:
        """
        Visits https://www.textnow.com/messaging with the connect.sid cookie
        to fetch XSRF-TOKEN and _csrf cookies.
        """
        ua = user_agent or DEFAULT_USER_AGENT
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        cookies = {"connect.sid": sid_cookie}
        try:
            resp = requests.get(
                "https://www.textnow.com/messaging",
                headers=headers,
                cookies=cookies,
                allow_redirects=True,
                timeout=15,
            )
            extracted = dict(resp.cookies)
            xsrf = extracted.get("XSRF-TOKEN")
            return extracted, xsrf
        except Exception:
            return {}, None
