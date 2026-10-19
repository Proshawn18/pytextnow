#!/usr/bin/env python3
"""
extract_from_bundle.py
======================
Extracts TextNow session cookies (specifically `connect.sid`, CSRF, and PerimeterX tokens)
from any bundle of requests—without launching or running any browser!

Can be used statically without any class object:
  from tools.extract_from_bundle import extract_from_raw_text, extract_and_save
  cookies, ua = extract_from_raw_text(raw_bundle_string)

Supported bundle formats:
  1. Exported HAR file (.har) from Chrome/Edge/Firefox DevTools
  2. Raw cURL command copied from DevTools Network tab
  3. Raw HTTP request headers text block
  4. Direct cookie string (Cookie: connect.sid=...; _csrf=...)
"""

import json
import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Tuple

from dotenv import load_dotenv

# Optionally load .env if present, but never require it
load_dotenv()

# Ensure pytextnow root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pythontextnow.util.SessionManager import SessionManager

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def parse_raw_cookie_string(cookie_header: str) -> Dict[str, str]:
    """Parse a 'Cookie: key=value; key2=val2' string into a dictionary."""
    cookies = {}
    # Strip leading 'Cookie:' or '-H Cookie:'
    cookie_header = re.sub(
        r"^(?:-H\s+)?['\"]?(?:Cookie:\s*)?",
        "",
        cookie_header.strip(),
        flags=re.IGNORECASE,
    )
    cookie_header = cookie_header.rstrip("'\";")

    for part in cookie_header.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, val = part.split("=", 1)
        key = key.strip()
        val = val.strip()
        # Clean quotes
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        cookies[key] = val
    return cookies


def extract_from_har(har_data: dict) -> Tuple[Dict[str, str], Optional[str]]:
    """Extract cookies and user-agent from a parsed HAR JSON object."""
    extracted_cookies = {}
    user_agent = None

    entries = har_data.get("log", {}).get("entries", [])
    for entry in reversed(entries):
        request = entry.get("request", {})
        url = request.get("url", "")
        if "textnow.com" not in url:
            continue

        for h in request.get("headers", []):
            name = h.get("name", "").lower()
            val = h.get("value", "")
            if name == "user-agent" and not user_agent:
                user_agent = val
            elif name == "cookie":
                cookies = parse_raw_cookie_string(val)
                extracted_cookies.update(cookies)

        for c in request.get("cookies", []):
            c_name = c.get("name")
            c_val = c.get("value")
            if c_name and c_val:
                extracted_cookies[c_name] = c_val

        if "connect.sid" in extracted_cookies:
            break

    return extracted_cookies, user_agent


def extract_from_curl(curl_cmd: str) -> Tuple[Dict[str, str], Optional[str]]:
    """Extract cookies and user-agent from a cURL command string."""
    cookies = {}
    user_agent = None

    ua_match = re.search(
        r"-H\s+['\"]User-Agent:\s*([^'\"]+)['\"]", curl_cmd, re.IGNORECASE
    )
    if ua_match:
        user_agent = ua_match.group(1).strip()

    cookie_matches = re.findall(
        r"-H\s+['\"]Cookie:\s*([^'\"]+)['\"]", curl_cmd, re.IGNORECASE
    )
    for c_str in cookie_matches:
        cookies.update(parse_raw_cookie_string(c_str))

    cookie_flag_matches = re.findall(
        r"--cookie\s+['\"]([^'\"]+)['\"]", curl_cmd, re.IGNORECASE
    )
    for c_str in cookie_flag_matches:
        cookies.update(parse_raw_cookie_string(c_str))

    return cookies, user_agent


def extract_from_raw_text(text: str) -> Tuple[Dict[str, str], Optional[str]]:
    """Extract cookies and user-agent from arbitrary text / request headers."""
    cookies = {}
    user_agent = None

    # 1. Try parsing as HAR JSON
    try:
        har_data = json.loads(text)
        if isinstance(har_data, dict) and "log" in har_data:
            return extract_from_har(har_data)
    except Exception:
        pass

    # 2. Try cURL pattern
    if "curl" in text.lower():
        c_cookies, c_ua = extract_from_curl(text)
        if c_cookies:
            cookies.update(c_cookies)
        if c_ua:
            user_agent = c_ua

    # 3. Search for User-Agent header line
    if not user_agent:
        ua_match = re.search(r"User-Agent:\s*([^\r\n]+)", text, re.IGNORECASE)
        if ua_match:
            user_agent = ua_match.group(1).strip()

    # 4. Search for Cookie header lines
    cookie_lines = re.findall(
        r"(?:^|\n)\s*(?:Cookie:|-H\s+['\"]Cookie:)\s*([^\r\n'\"]+)", text, re.IGNORECASE
    )
    for line in cookie_lines:
        cookies.update(parse_raw_cookie_string(line))

    # 5. Search directly for connect.sid=...
    if "connect.sid" not in cookies:
        sid_match = re.search(r"connect\.sid=([^;\s\r\n\"']+)", text)
        if sid_match:
            cookies["connect.sid"] = sid_match.group(1).strip()

    # 6. Search for csrf / xsrf tokens
    if "XSRF-TOKEN" not in cookies:
        xsrf_match = re.search(r"XSRF-TOKEN=([^;\s\r\n\"']+)", text)
        if xsrf_match:
            cookies["XSRF-TOKEN"] = xsrf_match.group(1).strip()
    if "_csrf" not in cookies:
        csrf_match = re.search(r"_csrf=([^;\s\r\n\"']+)", text)
        if csrf_match:
            cookies["_csrf"] = csrf_match.group(1).strip()

    # 7. Search for PerimeterX tokens
    for px_name in ["_px3", "_pxvid", "_pxhd", "pxcts", "_pxde"]:
        if px_name not in cookies:
            px_match = re.search(rf"{px_name}=([^;\s\r\n\"']+)", text)
            if px_match:
                cookies[px_name] = px_match.group(1).strip()

    return cookies, user_agent


def save_and_update_project(
    username: str,
    cookies: Dict[str, str],
    user_agent: Optional[str] = None,
    update_env: bool = False,
    validate: bool = True,
) -> bool:
    """Save the cookies via SessionManager and optionally update .env."""
    sid = cookies.get("connect.sid")
    if not sid:
        print("[!] Error: No 'connect.sid' found in the parsed request bundle.")
        return False

    ua = user_agent or DEFAULT_USER_AGENT

    # 1. Update session storage via SessionManager
    SessionManager.save_session(username, cookies, ua)
    print(
        f"[+] Saved {len(cookies)} cookies to ~/.pythontextnow/session_{username}.json"
    )

    # 2. Update .env if requested and .env exists
    env_file = PROJECT_ROOT / ".env"
    if update_env and env_file.exists():
        try:
            content = env_file.read_text(encoding="utf-8")
            pattern = r"TEXTNOW_SID_COOKIE\s*=\s*[^\r\n]+"
            new_line = f"TEXTNOW_SID_COOKIE={sid}"
            if re.search(pattern, content):
                updated_content = re.sub(pattern, new_line, content)
            else:
                updated_content = content + f"\n{new_line}\n"
            if username and "TEXTNOW_USERNAME=" in updated_content:
                user_pattern = r"TEXTNOW_USERNAME\s*=\s*[^\r\n]+"
                updated_content = re.sub(
                    user_pattern, f"TEXTNOW_USERNAME={username}", updated_content
                )
            env_file.write_text(updated_content, encoding="utf-8")
            print("[+] Updated TEXTNOW_SID_COOKIE in .env!")
        except Exception as e:
            print(f"[!] Note: Could not update .env: {e}")

    # 3. Validate with TextNowAPI if requested
    if validate:
        print("\n[*] Validating session against TextNow API...")
        try:
            from pythontextnow import Client
            from pythontextnow.api.TextNowAPI import TextNowAPI

            Client.set_client_config(username=username, sid_cookie=sid, user_agent=ua)
            api = TextNowAPI()
            user = api.get_user()
            print("[+] SUCCESS! Session is active and authenticated!")
            print(f"    - Username:        {user.username}")
            print(f"    - Assigned Number: {user.phone_number}")
            print(f"    - Account Email:   {user.email}")
            print(f"    - User ID:         {user.user_id}")
            return True
        except Exception as e:
            print(f"[!] Verification check returned: {e}")
            print(
                "[*] Note: The cookie was saved. If TextNow requires cooldown, try running in a moment."
            )
            return False
    return True


def extract_and_save(
    raw_bundle: str,
    username: Optional[str] = None,
    update_env: bool = False,
    validate: bool = True,
) -> Tuple[Dict[str, str], Optional[str]]:
    """
    Static helper function to parse any request bundle string and save session.

    Returns:
        (cookies_dict, user_agent)
    """
    cookies, user_agent = extract_from_raw_text(raw_bundle)
    if cookies and username:
        save_and_update_project(
            username, cookies, user_agent, update_env=update_env, validate=validate
        )
    return cookies, user_agent


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="TextNow connect.sid Extractor (Static Utility)"
    )
    parser.add_argument("--username", default=None, help="TextNow username")
    parser.add_argument(
        "--bundle", default=None, help="Bundle text or path to HAR/cURL file"
    )
    parser.add_argument(
        "--update-env", action="store_true", help="Update .env file on success"
    )
    args = parser.parse_args()

    print("=" * 60)
    print(" TextNow connect.sid Extractor (Zero Browser Overhead)")
    print("=" * 60)

    target_username = args.username or os.environ.get("TEXTNOW_USERNAME")
    if not target_username:
        target_username = input(
            "Enter TextNow username (or press Enter if configured later): "
        ).strip()

    raw_input_text = args.bundle or ""

    if not raw_input_text:
        print("\nPlease paste your request bundle below.")
        print(
            "(You can paste a cURL command, raw HTTP request headers, a HAR file path, or the Cookie string)"
        )
        print(
            "When finished, press Enter, then Ctrl+Z (Windows) or Ctrl+D, and press Enter:\n"
        )
        try:
            raw_input_text = sys.stdin.read()
        except KeyboardInterrupt:
            print("\nAborted.")
            return

    if not raw_input_text.strip():
        print("[!] No input provided. Exiting.")
        return

    # Check if input was a path to a file
    p = Path(raw_input_text.strip().strip('"').strip("'"))
    if p.exists() and p.is_file():
        print(f"[*] Loading file: {p.resolve()}")
        raw_input_text = p.read_text(encoding="utf-8", errors="ignore")

    print("[*] Parsing request bundle...")
    cookies, user_agent = extract_from_raw_text(raw_input_text)

    if not cookies or "connect.sid" not in cookies:
        print("\n[!] Could not find 'connect.sid' in the provided input.")
        print("Found cookies:", list(cookies.keys()))
        print("\nTip: In your browser DevTools -> Network tab:")
        print("  1. Click on any request to textnow.com (e.g. messaging or api/users)")
        print(
            "  2. Right click -> Copy -> Copy as cURL (bash), or copy the 'Cookie:' header"
        )
        print("  3. Run this script and paste it in!")
        return

    print(f"[+] Successfully extracted {len(cookies)} cookies:")
    print(f"    - connect.sid: {cookies['connect.sid'][:30]}...")
    if "XSRF-TOKEN" in cookies:
        print(f"    - XSRF-TOKEN:  {cookies['XSRF-TOKEN'][:20]}...")

    save_and_update_project(
        target_username, cookies, user_agent, update_env=args.update_env
    )


if __name__ == "__main__":
    main()
