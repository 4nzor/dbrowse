import time
from typing import List, Optional

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import ValidationError, Validator

status_messages: List[str] = []
MAX_STATUS_MESSAGES = 30


def push_status(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    status_messages.append(f"[{timestamp}] {message}")
    if len(status_messages) > MAX_STATUS_MESSAGES:
        del status_messages[: len(status_messages) - MAX_STATUS_MESSAGES]


class IntValidator(Validator):
    def validate(self, document) -> None:
        text = document.text.strip()
        if not text:
            raise ValidationError(message="Значение не может быть пустым")
        if not text.isdigit():
            raise ValidationError(message="Введите целое число")


def print_header(text: str) -> None:
    print()
    print("=" * 80)
    print(text)
    print("=" * 80)


def input_with_default(
    message: str,
    default: Optional[str] = None,
    is_password: bool = False,
    validator: Optional[Validator] = None,
    completer: Optional[WordCompleter] = None,
) -> str:
    suffix = f" [{default}]" if default is not None else ""
    full_message = f"{message}{suffix}: "
    text = prompt(
        full_message,
        is_password=is_password,
        validator=validator,
        validate_while_typing=False if validator else None,
        completer=completer,
    ).strip()
    if not text and default is not None:
        return str(default)
    return text


def format_size(num_bytes: int) -> str:
    if num_bytes is None:
        return "0 B"
    num = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(num)} {unit}"
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{int(num)} B"

