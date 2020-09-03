# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Action Completer.

A fairly simple method for registering callables as prompt-toolkit completions
"""

from .completer import ActionCompleter
from .types import Action, ActionGroup, ActionParam
from .validator import ActionValidator

__all__ = ["Action", "ActionGroup", "ActionParam", "ActionCompleter", "ActionValidator"]
