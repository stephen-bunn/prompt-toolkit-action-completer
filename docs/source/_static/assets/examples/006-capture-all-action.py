from prompt_toolkit.shortcuts import prompt

from action_completer import ActionCompleter

completer = ActionCompleter()


@completer.action("hello", capture_all=True)
@completer.param(["Mark", "John", "William"])
def _hello_name(name: str, *args):
    print(f"Hello, {name!s}!")
    print(f"Additional: {args!s}")


prompt_result = prompt(">>> ", completer=completer, validator=completer.get_validator())
completer.run_action(prompt_result)
