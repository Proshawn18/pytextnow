"""
Auto-Responder Example using pythontextnow
Demonstrates listening for incoming unread messages and replying automatically using the TextNow client.
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

# 1. Grab environment variables
load_dotenv()
username = os.getenv("TEXTNOW_USERNAME")
sid_cookie = os.getenv("TEXTNOW_SID_COOKIE")
recipient_phone = os.getenv("TEXTNOW_RECIPIENT_PHONE")

if not username or not sid_cookie or not recipient_phone:
    print("[!] Configuration required:")
    print(
        "    Please configure TEXTNOW_USERNAME, TEXTNOW_SID_COOKIE, and TEXTNOW_RECIPIENT_PHONE in .env"
    )
    sys.exit(1)

from pythontextnow import TextNow
from pythontextnow.enum import MessageDirection
from pythontextnow.model import TextMessage

# 2. Pass them explicitly to TextNow
client = TextNow(username=username, sid_cookie=sid_cookie)


def run_auto_responder(tn: TextNow, target_phone: str, poll_interval: int = 5):
    print(
        f"[*] Starting auto-responder for {target_phone} (Polling every {poll_interval}s)..."
    )
    print("[*] Press Ctrl+C to stop.\n")

    try:
        while True:
            messages = tn.get_messages(phone_number=target_phone, limit=5)
            for msg in messages:
                if msg.message_direction == MessageDirection.INCOMING and not msg.read:
                    text = (
                        msg.text if isinstance(msg, TextMessage) else "[Media message]"
                    )
                    print(f"[+] Received incoming message from {msg.number}: '{text}'")

                    # Mark incoming message as read
                    tn.mark_as_read(message=msg)

                    # Send automated reply
                    reply_text = "Thanks for your message! This is an automated reply."
                    tn.send_sms(to=target_phone, message=reply_text)
                    print(f"    -> Sent auto-reply: '{reply_text}'")

            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\n[*] Auto-responder stopped.")


if __name__ == "__main__":
    run_auto_responder(client, target_phone=recipient_phone, poll_interval=5)
