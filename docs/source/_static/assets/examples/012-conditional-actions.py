from prompt_toolkit.filters import Condition
from prompt_toolkit.shortcuts import prompt

from action_completer import ActionCompleter

completer = ActionCompleter()


ACTIVE: bool = False


def is_active() -> bool:
    return ACTIVE


def set_active(state: bool) -> bool:
    global ACTIVE
    ACTIVE = state
    return ACTIVE


@completer.action("activate", active=Condition(lambda: not is_active()))
def _activate_action():
    set_active(True)


@completer.action("deactivate", active=Condition(is_active))
def _deactivate_action():
    set_active(False)


@completer.action("hello", active=Condition(is_active))
def _hello_world():
    print("Hello, World!")


while True:
    prompt_result = prompt(
        ">>> ", completer=completer, validator=completer.get_validator()
    )
    completer.run_action(prompt_result)
