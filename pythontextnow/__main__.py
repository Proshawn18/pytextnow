"""
pythontextnow CLI Entry Point
Run with: python -m pythontextnow
"""

import subprocess
import sys
from pathlib import Path

from pythontextnow._version import __version__

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_RUN = PROJECT_ROOT / "tools" / "run.py"


def main():
    print(f"pythontextnow v{__version__} - Modern TextNow API Wrapper")
    print("-" * 55)
    try:
        from pythontextnow.tools.run import main as run_tools

        run_tools()
    except Exception:
        if TOOLS_RUN.exists():
            subprocess.run([sys.executable, str(TOOLS_RUN)])
        else:
            print("Usage:")
            print("  from pythontextnow import TextNow")
            print("  client = TextNow(username='...', sid_cookie='...')")


if __name__ == "__main__":
    main()
