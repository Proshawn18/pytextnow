#!/usr/bin/env python3
"""
direct_http_login.py
====================
Attempts direct HTTP authentication against TextNow's session endpoint:
  POST https://www.textnow.com/api/sessions

Can be used statically without any class object:
  from tools.direct_http_login import attempt_login
  attempt_login("user@email.com", "my_password")

Or run directly via CLI:
  python tools/direct_http_login.py --username user@email.com --password my_password
"""

import argparse
import getpass
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

# Optionally load .env if present, but never require it
load_dotenv()

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (
    SCRIPT_DIR.parent
    if (SCRIPT_DIR.parent / "setup.py").exists()
    else SCRIPT_DIR.parent.parent
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def attempt_login(
    username: str,
    password: str,
    cookies: Optional[dict] = None,
    update_env: bool = False,
    user_agent: Optional[str] = None,
    verbose: bool = True,
) -> bool:
    """
    Attempts direct HTTP login against POST https://www.textnow.com/api/sessions.

    Parameters:
        username (str): TextNow username or email.
        password (str): TextNow account password.
        cookies (Optional[dict]): Pre-existing session or telemetry cookies (e.g. _px3, _pxvid).
        update_env (bool): Whether to update .env with new connect.sid if login succeeds.
        user_agent (Optional[str]): Custom User-Agent header.
        verbose (bool): Print diagnostic output.

    Returns:
        bool: True if authentication succeeded and session was saved, False otherwise.
    """
    ua = user_agent or os.environ.get("TEXTNOW_USER_AGENT") or DEFAULT_USER_AGENT

    if verbose:
        print(f"[*] Attempting direct HTTP login for: {username}...")

    session = requests.Session()
    if cookies:
        session.cookies.update(cookies)
    session.headers.update(
        {
            "User-Agent": ua,
            "Origin": "https://www.textnow.com",
            "Referer": "https://www.textnow.com/login",
            "Accept": "application/json, text/plain, */*",
        }
    )

    # Step 1: Initial handshake to retrieve CSRF tokens & session cookies
    if verbose:
        print("[*] Step 1: Handshake with https://www.textnow.com/login...")
    try:
        session.get("https://www.textnow.com/login", timeout=12)
    except Exception as e:
        if verbose:
            print(f"[!] Network error connecting to TextNow: {e}")
        return False

    csrf_token = session.cookies.get("XSRF-TOKEN") or session.cookies.get("_csrf")
    if not csrf_token:
        if verbose:
            print("[!] Failed to obtain CSRF token from initial page.")
        return False

    session.headers.update(
        {
            "x-csrf-token": csrf_token,
            "x-xsrf-token": csrf_token,
            "Content-Type": "application/json",
        }
    )

    # Step 2: Post credentials to /api/sessions
    if verbose:
        print("[*] Step 2: Submitting credentials to POST /api/sessions...")
    payload = {
        "username": username,
        "password": password,
        "remember": True,
    }

    try:
        resp = session.post(
            "https://www.textnow.com/api/sessions", json=payload, timeout=15
        )
    except Exception as e:
        if verbose:
            print(f"[!] Network error submitting login: {e}")
        return False

    if verbose:
        print(f"[*] Server Response: HTTP {resp.status_code}")

    if resp.status_code == 200:
        sid = session.cookies.get("connect.sid")
        if verbose:
            print("[+] Direct Login SUCCESSFUL!")
            print(f"[+] Obtained connect.sid: {sid}")

        # Save session to ~/.pythontextnow/
        try:
            from pythontextnow.util.SessionManager import SessionManager

            SessionManager.save_session(username, session.cookies.get_dict(), ua)
            if verbose:
                print(
                    f"[+] Saved session to SessionManager (~/.pythontextnow/session_{username}.json)"
                )
        except Exception as e:
            if verbose:
                print(f"[!] Note: Could not save to SessionManager: {e}")

        # Optionally update .env
        env_file = PROJECT_ROOT / ".env"
        if update_env and env_file.exists() and sid:
            try:
                content = env_file.read_text(encoding="utf-8")
                pattern = r"TEXTNOW_SID_COOKIE\s*=\s*[^\r\n]+"
                new_line = f"TEXTNOW_SID_COOKIE={sid}"
                if re.search(pattern, content):
                    updated_content = re.sub(pattern, new_line, content)
                else:
                    updated_content = content + f"\n{new_line}\n"
                env_file.write_text(updated_content, encoding="utf-8")
                if verbose:
                    print("[+] Updated TEXTNOW_SID_COOKIE in .env!")
            except Exception as e:
                if verbose:
                    print(f"[!] Note: Could not update .env: {e}")
        return True

    try:
        res_json = resp.json()
        error_code = res_json.get("error_code")
        result = res_json.get("result")
    except Exception:
        res_json = {}
        error_code = None
        result = resp.text

    if verbose:
        print(f"[!] Login Response Details:")
        print(f"    - Error Code: {error_code}")
        print(f"    - Result:     {result}")

        is_perimeterx = (
            error_code == "PERIMETERX_RESPONSE"
            or resp.status_code == 403
            or "PXK56WkC4O" in resp.text
            or "perimeterx" in resp.text.lower()
            or "_px3" in resp.text
        )

        if error_code == "ACCOUNT_REGISTERED_WITH_APPLE":
            print("\n" + "=" * 60)
            print(" DIAGNOSIS: ACCOUNT_REGISTERED_WITH_APPLE")
            print("=" * 60)
            print(" This TextNow account was registered with Apple Sign-In.")
            print(" It has no native password stored on TextNow.")
            print(
                " Solution: Use extract_from_bundle.py to copy session from your browser."
            )
            print("=" * 60)
        elif is_perimeterx:
            print("\n" + "=" * 60)
            print(" DIAGNOSIS: PERIMETERX BOT CHALLENGE (HTTP 403)")
            print("=" * 60)
            print(
                " TextNow's WAF (PerimeterX/HUMAN Security) blocked this raw HTTP request"
            )
            print(
                " because it lacks client-side browser telemetry (canvas/WebGL/mouse)."
            )
            print(" ")
            print(" Solutions:")
            print(
                "  1. Recommended Flow: Use 'tools/extract_from_bundle.py' once to copy"
            )
            print(
                "     cookies from your browser, then run 'session_keepalive.py' to keep"
            )
            print("     the session alive indefinitely without logging in again.")
            print(
                "  2. Telemetry Cookie: If using a bot-solver proxy, pass your active"
            )
            print("     _px3 cookie via the cookies parameter.")
            print("=" * 60)

    return False


def main():
    parser = argparse.ArgumentParser(
        description="Direct HTTP Login to TextNow (Static Utility)"
    )
    parser.add_argument("--username", default=None, help="TextNow username or email")
    parser.add_argument("--password", default=None, help="TextNow account password")
    parser.add_argument(
        "--update-env", action="store_true", help="Update .env file on success"
    )
    args = parser.parse_args()

    print("=" * 60)
    print(" TextNow Direct HTTP Login (Zero Browser Overhead)")
    print("=" * 60)

    username = args.username or os.environ.get("TEXTNOW_USERNAME")
    if not username:
        username = input("Enter TextNow username or email: ").strip()

    password = args.password or os.environ.get("TEXTNOW_PASSWORD")
    if not password:
        password = getpass.getpass("Enter TextNow password: ")

    if not username or not password:
        print("[!] Error: Username and password are required.")
        sys.exit(1)

    attempt_login(username, password, update_env=args.update_env)


if __name__ == "__main__":
    main()
