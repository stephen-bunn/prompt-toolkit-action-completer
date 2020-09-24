# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains utility functions used throughout various points of the module."""

import re
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple, Union

from fuzzywuzzy import process as fuzzy_process
from fuzzywuzzy import utils as fuzzy_utils
from prompt_toolkit.formatted_text import FormattedText, to_formatted_text

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


def format_dynamic_value(template: str, text: str) -> str:
    """Format the given template text for the dynamic value.

    Args:
        template (str): The template text to be formatted
        text (str): The current text fragment that triggered the completion

    Returns:
        str: The formatted text
    """

    formats: Dict[str, str] = {"completion": text}

    result = template
    for format_key, format_value in formats.items():
        try:
            result = result.format(**{format_key: format_value})
        except (ValueError, IndexError):
            pass

    return result


def get_dynamic_value(
    source: ActionCompletable_T,
    value: LazyText_T,
    text: str,
    default: Optional[Union[str, FormattedText]] = None,
) -> Optional[Union[str, FormattedText]]:
    """Resolve a lazy/dynamic completion format value.

    The given value will be formatted in place of any ``{completion}`` usage
    within the dynamic text. The following example will display the description
    containing the completion value in place of the given value

    .. code-block:: python

        @completer.action("hello-world")
        @completer.param(["1", "2", "3"], display_meta="Will display {completion}")
        def _hello_world(number_value: str):
            print(f"Hello, {number_value!s}!")


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

    if isinstance(value, str):
        return format_dynamic_value(value, text)
    elif isinstance(value, FormattedText):
        return FormattedText(
            [
                (  # type: ignore
                    tuple_style,
                    format_dynamic_value(tuple_text, text),
                    *tuple_args,
                )
                for (tuple_style, tuple_text, *tuple_args) in value
            ]
        )
    elif callable(value):
        return value(source, text)

    return default


def get_best_choice(choices: Iterable[str], user_value: str) -> Optional[str]:
    """Guess the best choice from an interable of choice strings given a target value.

    This method has a few caveats to make using it with completion a bit easier:

    - If no choices are given, nothing is returned.
    - If only 1 choice is given, that choice is always returned.
    - If the given value (taget) text is not alphanumerical, the first available choice
      is returned.

    Args:
        choices (Iterable[str]): The iterable of choices to guess from
        user_value (str): The target value to base the best guess off of

    Returns:
        Optional[str]: The best choice if available, otherwise None
    """

    choices = list(choices)
    if len(choices) <= 0:
        return None

    if len(choices) == 1:
        return choices[0]

    if len(fuzzy_utils.full_process(user_value)) <= 0:
        return choices[0]

    extracted = fuzzy_process.extractOne(user_value, choices)
    return extracted[0] if extracted and len(extracted) > 0 else None


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
    - If the given value (target) text is not alphanumerical, all choices are yielded.

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

    # if value is reduced to nothing in fuzzy matching, yield all choices
    # NOTE: full_process doesn't consider _ (underscore) to be punctuation
    if len(fuzzy_utils.full_process(user_value)) <= 0:
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
