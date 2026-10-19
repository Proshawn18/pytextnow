#!/usr/bin/env python3
"""
run.py
======
Master CLI for TextNow Session Extraction & Keepalive (Zero Browser Overhead).
"""

import sys
import os
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "setup.py").exists() else SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def print_banner():
    print("\n" + "=" * 65)
    print("      TextNow Session & connect.sid Manager (Zero Browser)")
    print("=" * 65)
    print("  [1] Extract connect.sid from Request Bundle (cURL / HAR / Headers)")
    print("  [2] Refresh & Extend Session (Keepalive - 24hr renewal)")
    print("  [3] Attempt Direct HTTP Login (POST /api/sessions)")
    print("  [4] Verify Current Session & Account Info")
    print("  [5] Exit")
    print("=" * 65)


def check_status():
    from dotenv import load_dotenv
    load_dotenv()
    from pythontextnow.util.SessionManager import SessionManager

    print("\n[*] Checking TextNow Session Status...")
    username = os.environ.get("TEXTNOW_USERNAME")
    if not username:
        username = input("Enter TextNow username: ").strip()

    if not username:
        print("[!] No username provided.")
        return

    cookies = SessionManager.load_session(username)
    sid = cookies.get("connect.sid", "") or os.environ.get("TEXTNOW_SID_COOKIE", "")
    if not sid:
        sid = input(f"No cached session for '{username}'. Enter connect.sid (or press Enter to cancel): ").strip()
    if not sid:
        print(f"[!] No active session found for user '{username}'.")
        print("    Run Option [1] to extract your session.")
        return

    try:
        from pythontextnow import Client
        from pythontextnow.api.TextNowAPI import TextNowAPI

        Client.set_client_config(
            username=username,
            sid_cookie=sid,
        )

        api = TextNowAPI()
        user = api.get_user()
        print("\n[+] ACTIVE SESSION VERIFIED!")
        print(f"    - Username:        {user.username}")
        print(f"    - Phone Number:    {user.phone_number}")
        print(f"    - Email:           {user.email}")
        print(f"    - User ID:         {user.user_id}")
        print(f"    - connect.sid:     {sid[:30]}...")
    except Exception as e:
        print(f"[!] Session verification error: {e}")


def main():
    while True:
        print_banner()
        choice = input("Select an option (1-5): ").strip()

        if choice == "1":
            subprocess.run([sys.executable, str(SCRIPT_DIR / "extract_from_bundle.py")])
        elif choice == "2":
            subprocess.run([sys.executable, str(SCRIPT_DIR / "session_keepalive.py")])
        elif choice == "3":
            subprocess.run([sys.executable, str(SCRIPT_DIR / "direct_http_login.py")])
        elif choice == "4":
            check_status()
        elif choice == "5" or choice.lower() in ["exit", "q"]:
            print("\nGoodbye!")
            break
        else:
            print("[!] Invalid option. Please choose between 1 and 5.")


if __name__ == "__main__":
    main()
