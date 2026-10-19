"""
TextNow Automation Script using pythontextnow
Demonstrates primary use cases using the unified TextNow client:
1. Grabbing credentials from .env and passing them explicitly to TextNow(username=..., sid_cookie=...)
2. Account Info (username, assigned phone number)
3. Sending Text Messages (SMS)
4. Reading Recent Messages
5. Marking Messages as Read
6. Sending Media / MMS
7. Deleting Messages
8. Auto-responder / Polling
"""

import os
import sys
import time
from dotenv import load_dotenv

from pythontextnow import TextNow
from pythontextnow.enum import MessageDirection
from pythontextnow.model import TextMessage, MultiMediaMessage

# ---------------------------------------------------------------------------
# 1. Grab environment variables and pass explicitly to TextNow
# ---------------------------------------------------------------------------
load_dotenv()

USERNAME = os.getenv("TEXTNOW_USERNAME")
SID_COOKIE = os.getenv("TEXTNOW_SID_COOKIE")
RECIPIENT_PHONE = os.getenv("TEXTNOW_RECIPIENT_PHONE", "+12025550143")

if not USERNAME or not SID_COOKIE:
    print("[!] Configuration required:")
    print("    Please set TEXTNOW_USERNAME and TEXTNOW_SID_COOKIE in your .env file.")
    print("    See .env.example for a template.")
    sys.exit(1)

# Declare the client object with explicit credentials
client = TextNow(username=USERNAME, sid_cookie=SID_COOKIE)


def show_account_info(tn: TextNow):
    """Retrieve details about the logged-in TextNow account."""
    print("\n--- 1. Account Details ---")
    user = tn.get_user()
    print(f"Username:        {user.username}")
    print(f"Assigned Number: {user.phone_number}")
    print(f"User ID:         {user.user_id}")
    print(f"Account Email:   {user.email}")


def send_sms_example(tn: TextNow):
    """Send an SMS text message to the recipient."""
    print(f"\n--- 2. Sending SMS to {RECIPIENT_PHONE} ---")
    message_text = "Hello from the unified TextNow client!"
    tn.send_sms(to=RECIPIENT_PHONE, message=message_text)
    print(f"Sent: '{message_text}'")


def read_conversation_history(tn: TextNow, limit: int = 5):
    """Fetch and display the most recent messages from the recipient."""
    print(f"\n--- 3. Recent Messages (Last {limit}) ---")
    messages = tn.get_messages(phone_number=RECIPIENT_PHONE, limit=limit)
    for msg in messages:
        direction = "Outgoing (You)" if msg.message_direction == MessageDirection.OUTGOING else "Incoming"
        time_str = msg.datetime_.strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(msg, TextMessage):
            content = msg.text
        elif isinstance(msg, MultiMediaMessage):
            content = f"[Media: {msg.media}]"
        else:
            content = "[Unknown Message Format]"

        read_status = "Read" if msg.read else "Unread"
        print(f"[{time_str}] ({direction}) [ID: {msg.id_}] [{read_status}]: {content}")


def mark_unread_messages_as_read(tn: TextNow):
    """Find any unread incoming messages and mark them as read."""
    print("\n--- 4. Marking Unread Messages as Read ---")
    messages = tn.get_messages(phone_number=RECIPIENT_PHONE, limit=10)
    unread_found = False
    for msg in messages:
        if msg.message_direction == MessageDirection.INCOMING and not msg.read:
            print(f"Marking message {msg.id_} as read...")
            tn.mark_as_read(message=msg)
            unread_found = True
    if not unread_found:
        print("No unread incoming messages found.")


def send_media_example(tn: TextNow, file_path: str = None):
    """Send an image, video, or GIF to the recipient."""
    print(f"\n--- 5. Sending MMS / Media ---")
    if not file_path:
        print("Skipped: Provide a valid file path to send media.")
        return

    print(f"Sending media file: {file_path}")
    tn.send_mms(to=RECIPIENT_PHONE, file_path=file_path)
    print("Media sent successfully!")


# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # 1. Show Account Information
    # show_account_info(client)

    # 2. Send an SMS text message
    send_sms_example(client)

    # 3. Read back conversation history
    # read_conversation_history(client, limit=5)

    # 4. Mark unread messages as read
    # mark_unread_messages_as_read(client)

    # 5. Sending Media (uncomment when you have a file path)
    # send_media_example(client, file_path="sample.jpg")

    print("\nExecution complete!")