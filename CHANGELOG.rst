=========
Changelog
=========

| All notable changes to this project will be documented in this file.
| The format is based on `Keep a Changelog <http://keepachangelog.com/en/1.0.0/>`_ and this project adheres to `Semantic Versioning <http://semver.org/spec/v2.0.0.html>`_.
|

.. towncrier release notes start

`1.1.1 <https://github.com/stephen-bunn/prompt-toolkit-action-completer/releases/tag/v1.1.1>`_ (*2020-09-24*)
=============================================================================================================

Bug Fixes
---------

- Declaring dependency on ``typing-extensions`` in ``pyproject.toml``. `#5 <https://github.com/stephen-bunn/prompt-toolkit-action-completer/issues/5>`_


`1.1.0 <https://github.com/stephen-bunn/prompt-toolkit-action-completer/releases/tag/v1.1.0>`_ (*2020-09-24*)
=============================================================================================================

Features
--------

- Adding support for formatting ``{completion}`` in LazyText_T values for completions. `#4 <https://github.com/stephen-bunn/prompt-toolkit-action-completer/issues/4>`_

Bug Fixes
---------

- Ensuring that prompt text does not reduce to nothing before attempting to fuzzy match against explicit completions and validation. `#3 <https://github.com/stephen-bunn/prompt-toolkit-action-completer/issues/3>`_

Miscellaneous
-------------

- Moving ``ActionValidator._get_best_choice`` logic into ``utils.get_best_choice``.


`1.0.0 <https://github.com/stephen-bunn/prompt-toolkit-action-completer/releases/tag/v1.0.0>`_ (*2020-09-09*)
=============================================================================================================

Miscellaneous
-------------

- Adding the basic first release of the action completer that I have used in the past for personal projects. Note that this is currently untested and I have since lost the git history for this project (I know, I know...). 
- Creating full test-suite for most basic (non-edge case) functionality.
