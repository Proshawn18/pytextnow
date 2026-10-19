"""
Session Keepalive Example using pythontextnow
Demonstrates extending the TextNow session in background execution.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

from tools.session_keepalive import ensure_session_alive

USERNAME = os.environ.get("TEXTNOW_USERNAME")
if not USERNAME:
    print("[!] Please set TEXTNOW_USERNAME in your .env file.")
    sys.exit(1)

INTERVAL_HOURS = 6

if __name__ == "__main__":
    print(f"[*] Starting session keepalive daemon for user '{USERNAME}'...")
    print(f"[*] Refreshing every {INTERVAL_HOURS} hours (<0.5s HTTP ping).")
    print("[*] Press Ctrl+C to stop.\n")

    try:
        while True:
            success = ensure_session_alive(username=USERNAME)
            if success:
                print(f"[+] Session successfully extended for another 24 hours.")
            else:
                print("[!] Keepalive ping failed. Session may need re-extraction.")
            time.sleep(INTERVAL_HOURS * 3600)
    except KeyboardInterrupt:
        print("\n[*] Keepalive daemon stopped.")
