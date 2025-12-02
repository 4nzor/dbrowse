"""
Update checker for dbrowse.
Checks for new versions on GitHub and provides update functionality.
"""

import json
import subprocess
import sys
from typing import Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError

CURRENT_VERSION = "0.1.12"
GITHUB_REPO = "4nzor/dbrowse"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_latest_version() -> Optional[str]:
    """Get the latest version from GitHub releases."""
    try:
        request = Request(GITHUB_API_URL)
        request.add_header("Accept", "application/vnd.github.v3+json")
        
        with urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode())
            tag_name = data.get("tag_name", "")
            # Remove 'v' prefix if present
            return tag_name.lstrip("v")
    except (URLError, KeyError, json.JSONDecodeError, TimeoutError):
        return None


def compare_versions(current: str, latest: str) -> bool:
    """Compare version strings. Returns True if latest > current."""
    try:
        current_parts = [int(x) for x in current.split(".")]
        latest_parts = [int(x) for x in latest.split(".")]
        
        # Pad with zeros if needed
        max_len = max(len(current_parts), len(latest_parts))
        current_parts += [0] * (max_len - len(current_parts))
        latest_parts += [0] * (max_len - len(latest_parts))
        
        for c, l in zip(current_parts, latest_parts):
            if l > c:
                return True
            elif l < c:
                return False
        return False
    except (ValueError, AttributeError):
        return False


def check_for_updates() -> Tuple[bool, Optional[str]]:
    """Check if there's an update available.
    
    Returns:
        Tuple of (is_update_available, latest_version)
    """
    latest_version = get_latest_version()
    if not latest_version:
        return False, None
    
    if compare_versions(CURRENT_VERSION, latest_version):
        return True, latest_version
    
    return False, latest_version


def update_via_pip() -> bool:
    """Update dbrowse using pip."""
    try:
        print("Updating dbrowse...")
        # Try to update from GitHub if installed from git, otherwise from PyPI
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", f"git+https://github.com/{GITHUB_REPO}.git"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # If git install fails, try PyPI
        if result.returncode != 0:
            print("Trying PyPI...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "dbrowse"],
                capture_output=True,
                text=True,
                timeout=60
            )
        
        if result.returncode == 0:
            print("✅ dbrowse updated successfully!")
            print(f"Run 'dbrowse' to start the updated version.")
            return True
        else:
            print(f"❌ Update failed: {result.stderr}")
            return False
    except subprocess.TimeoutError:
        print("❌ Update timed out. Please try again.")
        return False
    except Exception as e:
        print(f"❌ Update error: {e}")
        return False


def update_via_brew() -> bool:
    """Update dbrowse using Homebrew."""
    try:
        print("Updating dbrowse via Homebrew...")
        result = subprocess.run(
            ["brew", "upgrade", "dbrowse"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print("✅ dbrowse updated successfully via Homebrew!")
            return True
        else:
            print(f"❌ Update failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Homebrew not found. Please install Homebrew first.")
        return False
    except subprocess.TimeoutError:
        print("❌ Update timed out. Please try again.")
        return False
    except Exception as e:
        print(f"❌ Update error: {e}")
        return False


def detect_installation_method() -> str:
    """Detect how dbrowse was installed (pip or brew)."""
    try:
        # Check if installed via brew
        result = subprocess.run(
            ["brew", "list", "dbrowse"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return "brew"
    except (FileNotFoundError, subprocess.TimeoutError):
        pass
    
    # Check if installed via pip
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "dbrowse"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return "pip"
    except subprocess.TimeoutError:
        pass
    
    return "unknown"


def update() -> bool:
    """Update dbrowse using the appropriate method."""
    method = detect_installation_method()
    
    if method == "brew":
        return update_via_brew()
    elif method == "pip":
        return update_via_pip()
    else:
        print("❌ Could not detect installation method.")
        print("Please update manually:")
        print("  - If installed via pip: pip install --upgrade dbrowse")
        print("  - If installed via brew: brew upgrade dbrowse")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        has_update, latest = check_for_updates()
        if has_update:
            print(f"Update available: {CURRENT_VERSION} -> {latest}")
            sys.exit(0)
        else:
            print(f"Already up to date: {CURRENT_VERSION}")
            sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "--update":
        success = update()
        sys.exit(0 if success else 1)
    else:
        print("Usage:")
        print("  python update_checker.py --check   # Check for updates")
        print("  python update_checker.py --update  # Update dbrowse")

