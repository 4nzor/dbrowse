import sys
from dotenv import load_dotenv

from database import ask_connection_config, save_connection_config
from ui import browse_connections_ui_once
from utils import print_header

load_dotenv()

# Import update checker (with fallback)
try:
    from update_checker import check_for_updates, update, CURRENT_VERSION
except ImportError:
    CURRENT_VERSION = "0.1.0"
    def check_for_updates():
        return False, None
    def update():
        print("Update functionality not available")


def main() -> None:
    # Handle --update flag
    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        from update_checker import update
        update()
        return
    
    # Check for updates (non-blocking, may fail silently)
    try:
        has_update, latest_version = check_for_updates()
    except Exception:
        has_update, latest_version = False, None
    
    print_header("dbrowse — terminal database browser")
    
    # Show update notification if available
    if has_update and latest_version:
        print(f"\n⚠️  Update available: v{latest_version} (current: v{CURRENT_VERSION})")
        print(f"   Run 'dbrowse --update' to update\n")

    while True:
        result = browse_connections_ui_once()
        if result == "add":
            cfg = ask_connection_config()
            save_connection_config(cfg)
            # loop continues and reopens the connection list
            continue
        else:
            break


if __name__ == "__main__":
    main()

