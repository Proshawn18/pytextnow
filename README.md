<div align="center">

<br>
<img src="https://raw.githubusercontent.com/joeyagreco/pythontextnow/main/img/pythontextnow_logo_.png" alt="pythontextnow logo" width="450"/>

### The Modern, Zero-Overhead TextNow API Client for Python
*Send and receive SMS/MMS, automate conversations, and persist sessions without running a browser.*

[TextNow Website](https://www.textnow.com/) • [Legal Disclaimer](DISCLAIMER.md) • [Report Issue](https://github.com/joeyagreco/pythontextnow/issues)

<a target="_blank" href="https://www.python.org/downloads/" title="Python version"><img src="https://img.shields.io/badge/python-%3E=_3.10-teal.svg"></a>
<img src="https://img.shields.io/badge/license-MIT-blue.svg">
<img src="https://img.shields.io/badge/tests-19%20passed-brightgreen.svg">

</div>

---

> [!WARNING]
> **Educational & Personal Use Only**: This is an unofficial, reverse-engineered library not affiliated with or endorsed by TextNow, Inc. Using automated tools on TextNow may violate their [Terms of Use](https://www.textnow.com/legal/terms). Read the [Legal Disclaimer](DISCLAIMER.md) before using this tool.

---

## Table of Contents
- [Why pythontextnow?](#why-pythontextnow)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Credentials & Authentication](#credentials--authentication)
- [The `TextNow` Client API](#the-textnow-client-api)
- [Zero-Browser Session Tools](#zero-browser-session-tools)
- [Automated Session Keepalive](#automated-session-keepalive)
- [Code Recipes](#code-recipes)
- [FAQ & Troubleshooting](#faq--troubleshooting)
- [Legacy Compatibility](#legacy-compatibility)
- [License](#license)

---

## Why pythontextnow?

Most public TextNow wrappers stopped working when TextNow introduced strict CSRF token validation, updated message payloads, and deployed anti-bot protections.

This library solves these hurdles:
- **Unified `TextNow` Class**: Simple, declarative client object (`client = TextNow(...)`).
- **Dynamic CSRF Management**: Automatically fetches fresh `XSRF-TOKEN` and `_csrf` cookies and recovers from 403 retries automatically.
- **Message Direction Fix**: Correctly maps modern TextNow direction IDs (`1` = Incoming, `2` = Outgoing).
- **No Browser Overhead**: Extract session cookies in seconds from browser DevTools without needing heavy Chromium, Selenium, or Playwright drivers.
- **Indefinite Sessions**: Includes a 24-hour rolling keepalive tool to keep your session alive forever.

---

## Installation

### From GitHub:
```bash
pip install git+https://github.com/<your-username>/pythontextnow.git
```

### For Local Development:
```bash
git clone https://github.com/<your-username>/pythontextnow.git
cd pythontextnow
pip install -e .
```

---

## Quick Start

### 1. Set Up Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your credentials:
```env
TEXTNOW_USERNAME=your_username
TEXTNOW_SID_COOKIE=s%3Ayour_connect_sid_cookie
TEXTNOW_RECIPIENT_PHONE=+12025550143
```

### 2. Send an SMS in 4 Lines
```python
import os
from dotenv import load_dotenv
from pythontextnow import TextNow

# 1. Grab environment variables
load_dotenv()
username = os.getenv("TEXTNOW_USERNAME")
sid_cookie = os.getenv("TEXTNOW_SID_COOKIE")

# 2. Instantiate client (auto_load_env is False by default for full explicit control)
client = TextNow(username=username, sid_cookie=sid_cookie)

# 3. Send SMS (E.164 format: +1XXXXXXXXXX)
client.send_sms(to="+12025550143", message="Hello from pythontextnow!")
```

---

## Credentials & Authentication

### Do any functions need your TextNow password?
**No.** TextNow's web messaging API **does not require or use your password**. Once you have your active `connect.sid` cookie, all messaging, reading, and account endpoints authenticate directly via that session cookie and derived CSRF tokens.

> *Note on `tools/direct_http_login.py`*: This repository includes an experimental script that attempts direct username/password login against TextNow's web login endpoint. However, TextNow's login endpoint is protected by PerimeterX bot detection (which flags raw HTTP calls lacking browser telemetry) and blocks accounts registered with Apple or Google Sign-In. **The recommended, 100% reliable method is extracting your `connect.sid` once using `tools/extract_from_bundle.py`.**

### How to get your `connect.sid`:
1. In your browser (Chrome/Edge/Firefox), go to [textnow.com/messaging](https://www.textnow.com/messaging).
2. Open **Developer Tools** (`F12`) $\rightarrow$ **Network** tab.
3. Refresh the page or click a conversation.
4. Right-click any request to `textnow.com` $\rightarrow$ **Copy** $\rightarrow$ **Copy as cURL (bash)** (or copy the `Cookie:` header).
5. Run the interactive extractor:
   ```bash
   python tools/extract_from_bundle.py
   ```
   Paste the bundle and press Enter $\rightarrow$ `Ctrl+Z` (Windows) or `Ctrl+D` (Mac/Linux) $\rightarrow$ Enter. Your session will be saved automatically!

---

## The `TextNow` Client API

### Initialization
```python
from pythontextnow import TextNow

# Recommended: pass variables explicitly
client = TextNow(
    username=username,
    sid_cookie=sid_cookie,
    user_agent=None,       # Optional: custom user agent
    auto_load_env=False    # Default: False. Set True to auto-read from os.environ
)
```

### `get_user() -> User`
Retrieves details about the authenticated account:
```python
user = client.get_user()
print(user.username)      # e.g., 'johndoe'
print(user.phone_number)  # e.g., '12025550143'
print(user.email)         # e.g., 'user@example.com'
print(user.user_id)       # e.g., 123456
```

### `send_sms(*, to: str, message: str) -> None`
Sends a text SMS message to a single recipient:
```python
client.send_sms(to="+12025550143", message="Hello!")
```

### `send_mms(*, to: str, file_path: str) -> None`
Sends media (PNG, JPG, MP4, GIF) to the recipient:
```python
client.send_mms(to="+12025550143", file_path="path/to/image.png")
```

### `get_messages(*, phone_number: str, limit: int = 10) -> list[Message]`
Fetches the most recent messages from a conversation with `phone_number`:
```python
from pythontextnow.enum import MessageDirection
from pythontextnow.model import TextMessage, MultiMediaMessage

messages = client.get_messages(phone_number="+12025550143", limit=5)
for msg in messages:
    direction = "Outgoing" if msg.message_direction == MessageDirection.OUTGOING else "Incoming"
    if isinstance(msg, TextMessage):
        print(f"[{msg.datetime_}] ({direction}) {msg.number}: {msg.text}")
    elif isinstance(msg, MultiMediaMessage):
        print(f"[{msg.datetime_}] ({direction}) [Media URL: {msg.media}]")
```

### `mark_as_read(message: Message) -> None`
Marks an incoming message as read:
```python
messages = client.get_messages(phone_number="+12025550143", limit=5)
for msg in messages:
    if msg.message_direction == MessageDirection.INCOMING and not msg.read:
        client.mark_as_read(msg)
```

### `delete_message(message_id: str) -> None`
Deletes a message from TextNow servers by its ID:
```python
client.delete_message(message_id="123456789")
```

### `get_conversation(phone_number: str | list[str]) -> ConversationService`
Returns the lower-level `ConversationService` for advanced generator-based paging:
```python
conv = client.get_conversation("+12025550143")
for batch in conv.get_messages(num_messages=30):
    for msg in batch:
        print(msg.text)
```

### `keepalive(update_env=False, verbose=False) -> bool`
Pings the TextNow server (<0.3s) to extend your session cookie expiration by an additional 24 hours:
```python
client.keepalive()
```

### `extract_and_update_session(raw_bundle: str) -> Tuple[dict, str]`
Extracts cookies from a pasted cURL/HAR bundle and updates this client's active session:
```python
client.extract_and_update_session(raw_curl_or_har_text)
```

---

## Static Usage (Without a Class Object)

If you prefer calling functions procedurally without declaring a `TextNow` class instance, you can use the static methods on `TextNow` or import directly from `tools`:

### Via `TextNow` Static Methods
```python
from pythontextnow import TextNow

# 1. Ping session keepalive statically
TextNow.ping_keepalive(username="my_user", sid_cookie="s%3Ayour_cookie")

# 2. Extract session cookies from cURL/HAR text statically
cookies, user_agent = TextNow.extract_session(raw_bundle_text, username="my_user")

# 3. Direct HTTP login attempt statically (Experimental / Advanced)
# Note: Subject to PerimeterX bot detection on TextNow's login endpoint.
success = TextNow.direct_login(username="my_user", password="my_password")
```

### Via Direct `tools` Imports
```python
from tools.session_keepalive import ping_and_extend_session
from tools.extract_from_bundle import extract_from_raw_text, extract_and_save
from tools.direct_http_login import attempt_login

# No .env required—all parameters can be passed explicitly:
ping_and_extend_session(username="my_user", sid_cookie="s%3A...")
cookies, ua = extract_from_raw_text(curl_text)
attempt_login(username="my_user", password="my_password")
```

---

## Zero-Browser Session Tools

Inside the [`tools/`](tools/) folder, each utility can be run directly from the command line **without strictly requiring a `.env` file** (accepts CLI flags or prompts interactively if flags are missing):

| Tool | Purpose | CLI Example (No `.env` Required) |
| :--- | :--- | :--- |
| `run.py` | Interactive master menu (1–5) | `python tools/run.py` |
| `extract_from_bundle.py` | Extracts cookies from cURL/HAR/Headers | `python tools/extract_from_bundle.py --username my_user` |
| `session_keepalive.py` | Renews session for another 24 hours | `python tools/session_keepalive.py --username my_user --sid s%3A...` |
| `direct_http_login.py` | *(Experimental)* Direct HTTP login attempt | `python tools/direct_http_login.py --username my_user --password pass` |

---

## Automated Session Keepalive

TextNow session cookies (`connect.sid`) expire after 24 hours. However, every authenticated request to TextNow's API rolls the expiration forward by another 24 hours.

Run the keepalive worker as a background daemon to keep your session valid indefinitely:
```bash
python tools/session_keepalive.py --username my_user --daemon --interval-hours 6
```


---

## Code Recipes

### Recipe 1: Inbound SMS Auto-Responder
Polls for new incoming messages and replies automatically:
```python
import os
import time
from dotenv import load_dotenv
from pythontextnow import TextNow
from pythontextnow.enum import MessageDirection
from pythontextnow.model import TextMessage

load_dotenv()
client = TextNow(
    username=os.getenv("TEXTNOW_USERNAME"),
    sid_cookie=os.getenv("TEXTNOW_SID_COOKIE")
)
target_phone = os.getenv("TEXTNOW_RECIPIENT_PHONE")

print("Starting auto-responder...")
while True:
    messages = client.get_messages(phone_number=target_phone, limit=5)
    for msg in messages:
        if msg.message_direction == MessageDirection.INCOMING and not msg.read:
            print(f"Received: {msg.text}")
            client.mark_as_read(msg)
            client.send_sms(to=target_phone, message="Thanks! This is an auto-reply.")
    time.sleep(5)
```

### Recipe 2: Server Alert Notifier
```python
import os
from dotenv import load_dotenv
from pythontextnow import TextNow

load_dotenv()
client = TextNow(
    username=os.getenv("TEXTNOW_USERNAME"),
    sid_cookie=os.getenv("TEXTNOW_SID_COOKIE")
)

def send_alert(alert_message: str):
    admin_phone = "+12025550143"
    client.send_sms(to=admin_phone, message=f"[ALERT] {alert_message}")

send_alert("Disk usage exceeded 90% on Server 1")
```

---

## FAQ & Troubleshooting

### Q: Why do I get `403 Forbidden` / `INVALID_CSRF_TOKEN`?
TextNow requires matching `XSRF-TOKEN` and `_csrf` cookies. The library handles this automatically: when a 403 occurs, it contacts the messaging handshake endpoint, retrieves fresh tokens, and transparently retries the request.

### Q: Why is my session cookie (`connect.sid`) expiring?
TextNow cookies expire 24 hours after their last use. Run `python tools/session_keepalive.py --daemon --interval-hours 6` or call `client.keepalive()` periodically.

### Q: Can my TextNow account be banned?
Yes. Sending spam, mass messaging, or dispatching texts faster than a human would triggers carrier spam filtering or account termination. Always enforce reasonable cooldowns between messages.

---

## Legacy Compatibility

If you have existing code using the original `joeyagreco/pythontextnow` API, it remains **100% compatible**:

```python
from pythontextnow import Client, ConversationService

# Legacy static configuration
Client.set_client_config(username="my_user", sid_cookie="s%3A...")

# Legacy conversation service
conv = ConversationService(conversation_phone_numbers=["+12025550143"])
conv.send_message(message="Legacy call still works!")
```

---

## Running Tests

Unit tests mock the network layer and do not make live calls to TextNow:
```bash
pytest
```

---

## License

This project is licensed under the [MIT License](LICENSE) - see the original attribution to Joey Greco.
