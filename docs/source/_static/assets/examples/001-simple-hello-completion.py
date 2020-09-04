from prompt_toolkit.shortcuts import prompt

from action_completer import ActionCompleter

completer = ActionCompleter()


@completer.action("hello")
def _hello_action():
    print("Hello, World!")


prompt_result = prompt(">>> ", completer=completer)
completer.run_action(prompt_result)
