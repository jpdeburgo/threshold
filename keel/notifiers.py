from typing import Protocol


class Notifier(Protocol):
    def notify(self, message: str) -> None: ...


class ConsoleNotifier:
    def notify(self, message: str) -> None:
        print(f"ALERT: {message}")
