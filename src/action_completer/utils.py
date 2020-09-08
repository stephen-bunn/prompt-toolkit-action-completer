# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains utility functions used throughout various points of the module."""

import re
from typing import Any, Generator, Iterable, List, Optional, Tuple, Union

from fuzzywuzzy import process as fuzzy_process
from prompt_toolkit.formatted_text import FormattedText

from .types import (
    Action,
    ActionCompletable_T,
    ActionContext_T,
    ActionGroup,
    ActionParam,
    LazyText_T,
)

DEFAULT_FUZZY_TOLERANCE = 75


def noop(*args, **kwargs) -> None:
    """Noop function that does absolutely nothing."""

    return None


def encode_completion(text: str) -> str:
    """Encode some completion text for writing to the user's current prompt buffer.

    Args:
        text (str): The text to encode for writing

    Returns:
        str: The properly encoded text for the user's prompt buffer
    """

    return text.replace(" ", "\\ ")


def decode_completion(text: str) -> str:
    """Reverse the encoding process for completion text.

    Args:
        text (str): The text to decode for use in action parameters and displaying

    Returns:
        str: The properly decoded text
    """

    return text.replace("\\ ", " ")


def get_fragments(text: str) -> List[str]:
    """Get the properly split fragments from the current user's prompt buffer.

    Args:
        text (str): The text of the current user's prompt buffer

    Returns:
        List[str]: A list of string fragments
    """

    return re.split(r"(?<!\\)\s+", text)


def extract_context(action_group: ActionGroup, fragments: List[str]) -> ActionContext_T:
    """Extract the current context for a root action group and buffer fragments.

    Args:
        action_group (ActionGroup): The root action group to start context extraction
        fragments (List[str]): The text fragments extracted from the current user's
            prompt buffer

    Returns:
        :data:`~action_completer.types.ActionContext_T`:
            A tuple of (parent ActionGroup, parent name, current ActionGroup/Action,
            list of remaining fragments [parameters])
    """

    current_parent: Optional[ActionGroup] = None
    current_name: Optional[str] = None
    current_completable: Union[ActionGroup, Action] = action_group
    depth = 0

    for fragment in fragments:
        if isinstance(current_completable, Action):  # pragma: no cover
            break

        for name, source in current_completable.children.items():
            if fragment == name:
                depth += 1
                current_parent = current_completable
                current_name = name

                if isinstance(source, Action):
                    # If the current action is inactive we need to go back 1 depth level
                    # so we are instead properly validating against the action's parent
                    # group along with the current fragments (even the ones that would
                    # be captured as part of the context extraction for the action).
                    #
                    # Otherwise, we would end up being unable to validate that defined
                    # and inactive actions were active in the ActionValidator.
                    active_fragment_depth = (
                        depth if source.active is None or source.active() else depth - 1
                    )
                    return (
                        current_parent,
                        current_name,
                        source,
                        fragments[active_fragment_depth:],
                    )
                elif isinstance(source, ActionGroup):  # pragma: no cover
                    current_completable = source

    return current_parent, current_name, current_completable, fragments[depth:]


def get_dynamic_value(
    source: ActionCompletable_T,
    value: LazyText_T,
    text: str,
    default: Optional[Union[str, FormattedText]] = None,
) -> Optional[Union[str, FormattedText]]:
    """Resolve a lazy/dynamic completion format value.

    Args:
        source (:data:`~action_completer.types.ActionCompletable_T`):
            The source for the completion
        value (:data:`~action_completer.types.LazyText_T`):
            The dynamic value that needs to be resolved for the source
        text (str):
            The current text fragment that triggered the given source
        default (Optional[Union[str, ~prompt_toolkit.formatted_text.FormattedText]]):
            A default if the given value resolves to None. Defaults to None.

    Returns:
        Optional[Union[str, ~prompt_toolkit.formatted_text.FormattedText]]:
            Either a string or :class:`~prompt_toolkit.formatted_text.FormattedText`
            instance if the value is properly resolved, otherwise defaults to the
            default
    """

    return (
        value
        if isinstance(value, (str, FormattedText))
        else (value(source, text) if callable(value) else default)
    )


def iter_best_choices(
    choices: Iterable[str], user_value: str, fuzzy_tolerance: Optional[int] = None
) -> Generator[str, None, None]:
    """Iterate over the sorted closest strings from some choices using fuzzy matching.

    This iterator has a few caveats that make using it with completion a bit easier:

    - If no choices are given, nothing is ever yielded.
    - If only 1 choice is given, that choice will always be yielded.

        Basically no fuzzy matching will occur against to allow for filtering out
        just a single choice.

    - If the given value (target) text is empty, all choices will be yielded.

    Args:
        choices (Iterable[str]): An interable of strings to apply fuzzy matching to
        user_value (str): The value to use for fuzzy comparison against choices
        fuzzy_tolerance (Optional[int], optional): The percentage integer 0-100 to
            tolerate the resulting fuzzy matches. Defaults to None.

    Yields:
        str: Sorted best matching strings from choices in comparison to ``user_value``
    """

    choices = list(choices)
    if len(choices) <= 0:
        return

    # always yield the choice if it is the only one available
    if len(choices) == 1:
        yield choices[0]
        return

    # if no value is given, yield all choices
    if not user_value or len(user_value) <= 0:
        yield from choices
        return

    for choice, confidence in fuzzy_process.extract(
        user_value, choices, limit=len(choices)
    ):
        if confidence is None or confidence < (
            fuzzy_tolerance or DEFAULT_FUZZY_TOLERANCE
        ):
            continue

        yield choice
