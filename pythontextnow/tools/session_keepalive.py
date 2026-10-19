#!/usr/bin/env python3
"""
session_keepalive.py
====================
Maintains TextNow session validity indefinitely with ZERO browser overhead.

Can be used statically without any class object:
  from tools.session_keepalive import ping_and_extend_session
  ping_and_extend_session(username="my_user", sid_cookie="s%3A...")

How it works:
  Every call to `GET https://www.textnow.com/api/users/{username}` returns
  a refreshed `Set-Cookie: connect.sid=...` that rolls the expiration forward
  by another 24 hours.

Usage:
  1. Single check and extension:
     python tools/session_keepalive.py --username my_user

  2. Continuous background keepalive (refreshes every 6 hours):
     python tools/session_keepalive.py --username my_user --daemon --interval-hours 6
"""

import os
import sys
import time
import argparse
import json
import re
from pathlib import Path
from typing import Optional, Tuple, Dict
import requests
from dotenv import load_dotenv

# Optionally load .env if present, but never require it
load_dotenv()

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "setup.py").exists() else SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pythontextnow.util.SessionManager import DEFAULT_USER_AGENT, SessionManager


def load_session(username: str) -> Tuple[dict, str]:
    session_file = SessionManager.get_session_file(username)
    if not session_file or not session_file.exists():
        cwd_file = PROJECT_ROOT / f".textnow_session_{username}.json"
        if not cwd_file.exists():
            raise FileNotFoundError(f"Session file not found for user '{username}'. Run extract_from_bundle.py first.")
        target = cwd_file
    else:
        target = session_file

    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cookies", {}), data.get("user_agent", DEFAULT_USER_AGENT)


def save_session(username: str, cookies: dict, user_agent: str, new_sid: Optional[str] = None, update_env: bool = False):
    if new_sid:
        cookies["connect.sid"] = new_sid

    SessionManager.save_session(username, cookies, user_agent)

    if new_sid and update_env:
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            try:
                content = env_file.read_text(encoding="utf-8")
                pattern = r'TEXTNOW_SID_COOKIE\s*=\s*[^\r\n]+'
                new_line = f'TEXTNOW_SID_COOKIE={new_sid}'
                if re.search(pattern, content):
                    updated_content = re.sub(pattern, new_line, content)
                else:
                    updated_content = content + f"\n{new_line}\n"
                env_file.write_text(updated_content, encoding="utf-8")
                print("[+] Updated TEXTNOW_SID_COOKIE in .env!")
            except Exception as e:
                print(f"[!] Note: Could not update .env: {e}")


def ping_and_extend_session(
    username: Optional[str] = None,
    sid_cookie: Optional[str] = None,
    user_agent: Optional[str] = None,
    update_env: bool = False,
    verbose: bool = True,
) -> bool:
    """
    Send a lightweight ping (<0.3s) to extend the connect.sid session for another 24h.
    Can be called completely statically with explicit username and sid_cookie,
    or falls back to SessionManager/environment.
    """
    user = username or os.environ.get("TEXTNOW_USERNAME")
    if not user:
        if verbose:
            print("[!] Error: Username is required for keepalive ping.")
        return False

    ua = user_agent or os.environ.get("TEXTNOW_USER_AGENT") or DEFAULT_USER_AGENT
    cookies = {}

    if sid_cookie:
        cookies = {"connect.sid": sid_cookie}
    else:
        try:
            loaded_cookies, loaded_ua = load_session(user)
            cookies = loaded_cookies
            if loaded_ua:
                ua = loaded_ua
        except FileNotFoundError as e:
            if verbose:
                print(f"[!] {e}")
            return False

    sid = cookies.get("connect.sid")
    if not sid:
        if verbose:
            print("[!] No connect.sid available for keepalive ping.")
        return False

    headers = {
        "User-Agent": ua,
        "Origin": "https://www.textnow.com",
        "Referer": "https://www.textnow.com/messaging",
        "Accept": "application/json, text/plain, */*",
    }
    if "XSRF-TOKEN" in cookies:
        headers["x-csrf-token"] = cookies["XSRF-TOKEN"]
        headers["x-xsrf-token"] = cookies["XSRF-TOKEN"]

    url = f"https://www.textnow.com/api/users/{user}"
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update(headers)

    start_time = time.time()
    try:
        resp = session.get(url, timeout=10)
        elapsed = time.time() - start_time
    except Exception as e:
        if verbose:
            print(f"[!] Network error pinging TextNow: {e}")
        return False

    if resp.status_code == 200:
        data = resp.json()
        new_sid = resp.cookies.get("connect.sid")
        set_cookie_header = resp.headers.get("set-cookie", "")

        # Look for expiration
        exp_match = re.search(r"Expires=([^;]+)", set_cookie_header)
        expires_info = exp_match.group(1) if exp_match else "Rolling 24 Hours"

        if verbose:
            print(f"[+] Keepalive OK ({elapsed:.2f}s) | Status: 200 OK")
            print(f"    - User:      {data.get('username')}")
            print(f"    - Number:    {data.get('phone_number')}")
            print(f"    - Expiration Extended: {expires_info}")

        if new_sid and new_sid != sid:
            if verbose:
                print(f"[*] New connect.sid issued by server: {new_sid[:25]}...")
            save_session(user, cookies, ua, new_sid=new_sid, update_env=update_env)
        else:
            save_session(user, cookies, ua, update_env=update_env)
        return True
    elif resp.status_code == 401 or resp.status_code == 403:
        if verbose:
            print(f"[!] Session expired or unauthorized (Status {resp.status_code}).")
            print(f"    Response: {resp.text[:200]}")
            print("[*] Tip: Use extract_from_bundle.py to refresh your session.")
        return False
    else:
        if verbose:
            print(f"[!] Unexpected response: {resp.status_code} - {resp.text[:200]}")
        return False


def ensure_session_alive(username: Optional[str] = None, sid_cookie: Optional[str] = None) -> bool:
    """Convenience function to be called before running messaging automations."""
    return ping_and_extend_session(username=username, sid_cookie=sid_cookie)


def main():
    parser = argparse.ArgumentParser(description="TextNow Zero-Overhead Session Keepalive (Static Utility)")
    parser.add_argument("--username", default=None, help="TextNow username")
    parser.add_argument("--sid", default=None, help="connect.sid cookie value")
    parser.add_argument("--daemon", action="store_true", help="Run indefinitely in background")
    parser.add_argument("--interval-hours", type=float, default=6.0, help="Interval between keepalive pings in daemon mode")
    parser.add_argument("--update-env", action="store_true", help="Update .env file if new connect.sid is issued")
    args = parser.parse_args()

    print("=" * 60)
    print(" TextNow Session Keepalive & Auto-Extender")
    print("=" * 60)

    username = args.username or os.environ.get("TEXTNOW_USERNAME")
    if not username:
        username = input("Enter TextNow username: ").strip()

    if not username:
        print("[!] Error: Username is required.")
        sys.exit(1)

    sid = args.sid or os.environ.get("TEXTNOW_SID_COOKIE")

    if not args.daemon:
        ping_and_extend_session(username=username, sid_cookie=sid, update_env=args.update_env)
    else:
        interval_sec = int(args.interval_hours * 3600)
        print(f"[*] Running in daemon mode for '{username}'. Pinging every {args.interval_hours} hours ({interval_sec} seconds).")
        print("[*] Press Ctrl+C to stop.\n")
        while True:
            ping_and_extend_session(username=username, sid_cookie=sid, update_env=args.update_env)
            print(f"[*] Sleeping for {args.interval_hours} hours...\n")
            time.sleep(interval_sec)


if __name__ == "__main__":
    main()
