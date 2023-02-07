import sys
from abc import ABC, abstractmethod


class UserInterface(ABC):
    @abstractmethod
    def show_message(self, msg: str, use_same_line: bool):
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
    def show_message(self, msg, use_same_line=False):
        if use_same_line:
            print(msg, end='\r\x1b[1K')
        else:
            print(msg)

    def show_error(self, msg):
        print(msg, file=sys.stderr)

    def ask(self, prompt: str) -> str:
        return input(prompt)

    def progress_bar(self, percent, fill = '█'):
        bar = fill * percent
        return bar

