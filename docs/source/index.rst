.. raw:: html

   <h1 align="center" style="font-size: 64px; margin-bottom: 0.5rem;">Action Completer</h1>
   <h4 align="center">A fairly simple method for registering callables as prompt-toolkit completions</h4>
   <p align="center">
      <a href="https://pypi.org/project/prompt-toolkit-action-completer/" target="_blank"><img alt="Supported Versions" src="https://img.shields.io/pypi/pyversions/prompt-toolkit-action-completer.svg"></a>
      <a href="https://github.com/stephen-bunn/prompt-toolkit-action-completer/actions?query=workflow%3A%22Test+Package%22" target="_blank"><img alt="Test Status" src="https://github.com/stephen-bunn/prompt-toolkit-action-completer/workflows/Test%20Package/badge.svg"></a>
      <a href="https://codecov.io/gh/stephen-bunn/prompt-toolkit-action-completer" target="_blank"><img alt="codecov" src="https://codecov.io/gh/stephen-bunn/prompt-toolkit-action-completer/branch/master/graph/badge.svg"></a>
      <a href="https://github.com/ambv/black" target="_blank"><img alt="Code Style: Black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
   </p>


.. code-block:: python

   from pathlib import Path

   from action_completer import ActionCompleter
   from prompt_toolkit.shortcuts import prompt
   from prompt_toolkit.completion import PathCompleter
   from prompt_toolkit.validation import Validator

   completer = ActionCompleter()


   @completer.action("cat")
   @completer.param(
      PathCompleter(),
      cast=Path,
      validators=[
         Validator.from_callable(
            lambda p: Path(p).is_file(),
            error_message="Path is not an existing file"
         )
      ]
   )
   def _cat_action(filepath: Path):
      with filepath.open("r") as file_handle:
         print(file_handle.read())


   prompt_result = prompt(
      ">>> ",
      completer=completer,
      validator=completer.get_validator()
   )
   completer.run_action(prompt_result)


.. image:: _static/assets/recordings/004-cat-path-validation.gif

**To get started using this package, please see the** :ref:`getting-started` **page!**

User Documentation
------------------

.. toctree::
   :maxdepth: 2

   getting-started
   contributing
   changelog
   license


Project Reference
-----------------

.. toctree::
   :maxdepth: 2

   action_completer
