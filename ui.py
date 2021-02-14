import sys
from abc import ABC, abstractmethod


class UserInterface(ABC):
    @abstractmethod
    def show_message(self, msg: str):
        pass

    @abstractmethod
    def show_error(self, msg: str):
        pass

    @abstractmethod
    def ask(self, prompt: str) -> str:
        pass

    @abstractmethod
    def progress_bar(self, percent: int, fill: str):
        pass


class ConsoleUserInterface(UserInterface):
    def show_message(self, msg):
        print(msg)

    def show_error(self, msg):
        print(msg, file=sys.stderr)

    def ask(self, prompt: str) -> str:
        return input(prompt)

    def progress_bar(self, percent, fill = '█'):
        bar = fill * percent
        return bar

