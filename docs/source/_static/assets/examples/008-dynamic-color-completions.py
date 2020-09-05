from prompt_toolkit.shortcuts import prompt

from action_completer import ActionCompleter, types

completer = ActionCompleter()


def dynamic_style(
    completable: types.ActionCompletable_T, completable_value: str
) -> str:
    if completable_value.lower() == "john":
        return "fg:white bg:blue"

    return "fg:white bg:red"


@completer.action("hello")
@completer.param(
    ["Mark", "John", "William"],
    style=dynamic_style,
    selected_style="bold",
)
def _hello_name(name: str):
    print(f"Hello, {name!s}!")


prompt_result = prompt(">>> ", completer=completer, validator=completer.get_validator())
completer.run_action(prompt_result)
