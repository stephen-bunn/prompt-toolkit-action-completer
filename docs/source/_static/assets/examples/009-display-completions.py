from prompt_toolkit.shortcuts import prompt

from action_completer import ActionCompleter

completer = ActionCompleter()


@completer.action("hello", display="Run hello world")
def _hello_world():
    print("Hello, World!")


prompt_result = prompt(">>> ", completer=completer, validator=completer.get_validator())
completer.run_action(prompt_result)
