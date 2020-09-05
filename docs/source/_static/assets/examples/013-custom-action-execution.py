from prompt_toolkit.shortcuts import prompt

from action_completer import ActionCompleter

completer = ActionCompleter()


@completer.action("hello")
@completer.param(["World", "Stephen"])
def _hello_action(name: str, *args):
    print(f"Hello, {name!s}!")
    print(f"Additional: {args!s}")


prompt_result = prompt(">>> ", completer=completer, validator=completer.get_validator())
action_partial = completer.get_partial_action(prompt_result)

print(action_partial)
action_partial("I'm something new")
