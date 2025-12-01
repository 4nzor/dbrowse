from dotenv import load_dotenv

from database import ask_connection_config, save_connection_config
from ui import browse_connections_ui_once
from utils import print_header

load_dotenv()


def main() -> None:
    print_header("dbrowse — мини-pgAdmin в терминале")

    while True:
        result = browse_connections_ui_once()
        if result == "add":
            cfg = ask_connection_config()
            save_connection_config(cfg)
            # цикл продолжится и заново откроет список баз
            continue
        else:
            break


if __name__ == "__main__":
    main()

