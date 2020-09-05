from pathlib import Path

from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.validation import Validator

from action_completer import ActionCompleter

completer = ActionCompleter()

hello_group = completer.group("hello")


@hello_group.action("world")
def _hello_world():
    print("Hello, World!")


@hello_group.action("custom")
@completer.param(None)
def _hello_custom(name: str):
    print(f"Hello, {name!s}!")


prompt_result = prompt(">>> ", completer=completer, validator=completer.get_validator())
completer.run_action(prompt_result)
