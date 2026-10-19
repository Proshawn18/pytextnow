# TextNow Session & connect.sid Manager (Zero Browser Overhead)

This folder contains lightweight, 100% browser-free Python tools to extract, maintain, and refresh your TextNow `connect.sid` session cookies without the overhead of running Chromium, Playwright, or Selenium.

---

## Quick Start (Interactive Menu)

Run the master interactive CLI:
```bash
python run.py
```

---

## Tools

### 1. Extract from Request Bundle (`extract_from_bundle.py`)
Extracts `connect.sid`, CSRF tokens, and session cookies from any pasted request or exported file.

**Usage:**
```bash
# Option A: Interactive prompt (paste your request or cURL directly)
python extract_from_bundle.py

# Option B: Pass a file (HAR file, headers.txt, or curl.txt)
python extract_from_bundle.py my_requests.har
```

**How to get the request bundle from your browser:**
1. In your browser (Chrome/Edge/Firefox), open **Developer Tools** (`F12`) $\rightarrow$ **Network** tab.
2. Visit or refresh any TextNow page (e.g. `textnow.com/messaging`).
3. Right click on any request to `textnow.com` $\rightarrow$ **Copy** $\rightarrow$ **Copy as cURL (bash)** or copy the `Cookie:` header.
4. Run `python extract_from_bundle.py`, paste it, and press Enter -> Ctrl+Z (Windows) or Ctrl+D (Linux/macOS) -> Enter.
5. The script automatically saves your session to `~/.pythontextnow/` and `.env`, and validates the session against the TextNow API.

---

### 2. Automatic Session Keepalive (`session_keepalive.py`)
TextNow sessions automatically extend by an additional 24 hours on every authenticated HTTP request. This tool sends a 0.5-second background request to keep your session permanently alive so you never have to re-login!

**Usage:**
```bash
# Single check and extension
python session_keepalive.py

# Run in background to ping every 6 hours
python session_keepalive.py --daemon --interval-hours 6
```

**In your code:**
```python
from tools.session_keepalive import ensure_session_alive

# Call before sending messages to ensure active session
ensure_session_alive()
```

---

### 3. Direct HTTP Login (`direct_http_login.py`)
Attempts direct HTTP authentication against `POST https://www.textnow.com/api/sessions`.

**Usage:**
```bash
python direct_http_login.py --username your_username
```

> **Note**: Accounts registered via **Sign in with Apple** do not have a native password stored on TextNow until you set one via TextNow's password reset flow. If this error is returned, use `extract_from_bundle.py` or request a password reset email to set a standard password.
