from pathlib import Path

from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.validation import Validator

from action_completer import ActionCompleter

completer = ActionCompleter()


@completer.action("cat")
@completer.param(
    PathCompleter(),
    cast=Path,
    validators=[
        Validator.from_callable(
            lambda p: Path(p).is_file(), error_message="Path is not an existing file"
        )
    ],
)
def _cat_action(filepath: Path):
    with filepath.open("r") as file_handle:
        print(file_handle.read())


prompt_result = prompt(">>> ", completer=completer, validator=completer.get_validator())
completer.run_action(prompt_result)
