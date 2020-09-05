from prompt_toolkit.shortcuts import prompt

from action_completer import ActionCompleter

completer = ActionCompleter()


@completer.action("hello")
@completer.param(
    ["Mark", "John", "William"],
    style="fg:white bg:red",
    selected_style="fg:red bg:white bold",
)
def _hello_name(name: str):
    print(f"Hello, {name!s}!")


prompt_result = prompt(">>> ", completer=completer, validator=completer.get_validator())
completer.run_action(prompt_result)
