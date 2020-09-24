from prompt_toolkit.shortcuts import prompt

from action_completer import ActionCompleter

completer = ActionCompleter()


@completer.action("hello")
@completer.param(["1", "2", "3"], cast=int, display_meta="Says hello to {completion}")
def _hello_action(num: int):
    print(f"Hello, {num!s}!")


prompt_result = prompt(">>> ", completer=completer, validator=completer.get_validator())
completer.run_action(prompt_result)
