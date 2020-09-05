from pathlib import Path
from typing import List

from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.validation import ValidationError, Validator

from action_completer import ActionCompleter, ActionParam

completer = ActionCompleter()


def _validate_touch(action_param: ActionParam, param_value: str, fragments: List[str]):
    dirpath = Path(fragments[0])
    filepath = dirpath.joinpath(f"{param_value!s}.txt")
    if filepath.is_file():
        raise ValidationError(message=f"File at {filepath!s} already exists")


@completer.action("touch")
@completer.param(
    PathCompleter(only_directories=True),
    cast=Path,
    validators=[
        Validator.from_callable(
            lambda p: Path(p).is_dir(), error_message="Not an existing directory"
        )
    ],
)
@completer.param(None, validators=[_validate_touch])
def _touch_txt_action(dirpath: Path, name: str):
    filepath = dirpath.joinpath(f"{name!s}.txt")
    with filepath.open("r") as file_handle:
        print(file_handle.read())


prompt_result = prompt(">>> ", completer=completer, validator=completer.get_validator())
completer.run_action(prompt_result)
