# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains useful composite strategies for usage throughout project tests."""

from string import ascii_letters, digits, printable, punctuation
from typing import Any, Dict, List, Optional, Type, Union

from hypothesis.strategies import (
    SearchStrategy,
    binary,
    booleans,
    builds,
    characters,
    complex_numbers,
    composite,
    dictionaries,
    floats,
    integers,
    just,
    lists,
    none,
    nothing,
    one_of,
    recursive,
    sampled_from,
    text,
    tuples,
)
from prompt_toolkit.filters import Condition, Filter
from prompt_toolkit.formatted_text import ANSI, HTML, FormattedText, to_formatted_text

from action_completer import ActionCompleter, types


@composite
def fragment(draw) -> SearchStrategy[str]:
    """Composite strategy for building a fragment-safe string."""

    return draw(text(alphabet=(ascii_letters + digits + punctuation), min_size=1))


@composite
def builtin_types(
    draw, include: Optional[List[Type]] = None, exclude: Optional[List[Type]] = None
) -> Any:
    """Composite strategy for building an instance of a builtin type.

    This strategy allows you to check against builtin types for when you need to do
    variable validation (which should be rare). By default this composite will generate
    all available types of builtins, however you can either tell it to only generate
    some types or exclude some types. You do this using the ``include`` and ``exclude``
    parameters.

    For example using the ``include`` parameter like the following will ONLY generate
    strings and floats for the samples:

    >>> @given(builtin_types(include=[str, float]))
    ... def test_only_strings_and_floats(value: Union[str, float]):
    ...     assert isinstance(value, (str, float))

    Similarly, you can specify to NOT generate Nones and complex numbers like the
    following example:

    >>> @given(builtin_types(exclude=[None, complex]))
    ... def test_not_none_or_complex(value: Any):
    ...     assert value and not isinstance(value, complex)
    """

    strategies: Dict[Any, SearchStrategy[Any]] = {
        None: none(),
        int: integers(),
        bool: booleans(),
        float: floats(allow_nan=False),
        tuple: builds(tuple),
        list: builds(list),
        set: builds(set),
        frozenset: builds(frozenset),
        str: text(),
        bytes: binary(),
        complex: complex_numbers(),
    }

    to_use = set(strategies.keys())
    if include and len(include) > 0:
        to_use = set(include)

    if exclude and len(exclude) > 0:
        to_use = to_use - set(exclude)

    return draw(
        one_of([strategy for key, strategy in strategies.items() if key in to_use])
    )


@composite
def action_param(draw, **kwargs) -> SearchStrategy[types.ActionParam]:
    """Composite strategy for building a basic :class:`~.types.ActionParam`."""

    return draw(builds(types.ActionParam, **kwargs))


@composite
def action(draw, **kwargs) -> SearchStrategy[types.Action]:
    """Composite strategy for building a basic :class:`~.types.Action`."""

    return draw(builds(types.Action, **kwargs))


@composite
def action_group_children(
    draw,
    key_strategy: Optional[SearchStrategy[str]] = None,
    action_strategy: Optional[SearchStrategy[types.Action]] = None,
    max_depth: int = 5,
    min_size: int = 0,
    max_size: int = 5,
) -> SearchStrategy[Dict[str, Union[types.ActionGroup, types.Action]]]:
    """Composite strategy for building an :class:`~.types.ActionGroup`'s children.

    This requires its own strategy since this is a recursive strategy and trying to
    embed this into the ``action_group`` strategy can be a nightmare.

    Args:
        key_strategy (Optiona[SearchStrategy[str]], optional): The strategy for
            generating fragment keys in the children dictionary (applies to all levels)
        action_strategy (Optional[SearchStrategy[types.Action]], optional): The strategy
            for generating :class:`~.types.Action` instances for leaf nodes of the
            children dictionary
        max_depth (int): The number of levels we are allowed to recurse down as nested
            action groups, defaults to 5
        min_size (int): The minimum allowed number of actions or action groups to exist
            on one level of the children dictionary, defaults to 0
        max_size (int): The maximum allowed number of actions or action groups to exist
            on one level of the children dictionary, defaults to 5

    Returns:
        SearchStrategy[Dict[str, Union[types.ActionGroup, types.Action]]]:
            The children dictionary that can be given to create an action group
    """

    return draw(
        recursive(
            dictionaries(
                (key_strategy if key_strategy else fragment()),  # type: ignore
                (action_strategy if action_strategy else action()),
                min_size=min_size,
                max_size=max_size,
            ),
            lambda children: dictionaries(
                (key_strategy if key_strategy else fragment()),  # type: ignore
                one_of(children, (action_strategy if action_strategy else action())),
                min_size=min_size,
                max_size=max_size,
            ),
            max_leaves=max_depth,
        )
    )


@composite
def action_group(draw, **kwargs) -> SearchStrategy[types.ActionGroup]:
    """Composite strategy for building a basic :class:`~.types.ActionGroup`."""

    children_strategy = kwargs.pop("children", None)
    return draw(
        builds(
            types.ActionGroup,
            children=(
                children_strategy if children_strategy else action_group_children()
            ),
            **kwargs,
        )
    )
