# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains tests related to the functionality provided in the utilities."""

import re
from string import printable
from typing import List, Optional, Type, Union
from unittest.mock import patch

from fuzzywuzzy import process as fuzzy_process
from hypothesis import assume, given
from hypothesis.strategies import just, lists, none, one_of, text
from prompt_toolkit.formatted_text import FormattedText

from action_completer import types
from action_completer.utils import (
    decode_completion,
    encode_completion,
    extract_context,
    get_dynamic_value,
    get_fragments,
    iter_best_choices,
    noop,
)

from .strategies import (
    action,
    action_group,
    action_param,
    builtin_types,
    fragment,
    lazy_string,
    lazy_text,
)


@given(builtin_types())
def test_noop(builtin_type: Type):
    assert callable(noop)
    assert noop() is None  # type: ignore
    assert noop(builtin_type) is None  # type: ignore

    try:
        assert noop(*iter(builtin_type)) is None  # type: ignore
    except TypeError:
        pass


@given(text(alphabet=printable))
def test_encode_decode_completion_is_reflective(text: str):
    assert decode_completion(encode_completion(text)) == text


@given(lists(fragment().filter(lambda value: "\\" not in value), min_size=1))  # type: ignore
def test_get_fragments(fragments: List[str]):
    extracted_fragments = get_fragments(" ".join(fragments))
    assert isinstance(extracted_fragments, list)
    assert len(extracted_fragments) == len(fragments)


@given(text())
def test_iter_best_choices_yields_nothing_if_given_nothing(user_value: str):
    assert list(iter_best_choices([], user_value)) == []


@given(text())
def test_iter_best_choices_yields_only_choice_if_given_one_choice(user_value: str):
    assert list(iter_best_choices(["test"], user_value)) == ["test"]  # type: ignore


@given(lists(fragment(), min_size=1), one_of(none(), text(max_size=0)))
def test_iter_best_choices_yields_all_choice_if_no_user_value_given(
    choices: List[str], user_value: Optional[str]
):
    assert list(iter_best_choices(choices, user_value)) == choices  # type: ignore


def test_iter_best_choices():
    with patch.object(fuzzy_process, "extract") as mocked_extract:
        mocked_extract.return_value = [
            ("none test", None),
            ("tolerance test", 0),
            ("test", 100),
        ]

        assert list(
            iter_best_choices(["none test", "tolerance test", "test"], "test", 100)
        ) == ["test"]


@given(
    one_of(action_param(), action(), action_group()),
    lazy_string(value_strategy=just("test")),
    text(alphabet=printable),
)
def test_get_dynamic_value_LazyString(
    source: types.ActionCompletable_T, lazy: types.LazyString_T, text: str
):
    assert get_dynamic_value(source, lazy, text) == "test"


@given(
    one_of(action_param(), action(), action_group()),
    lazy_text(allow_none=False),
    text(alphabet=printable),
)
def test_get_dynamic_value_LazyText(
    source: types.ActionCompletable_T, lazy: types.LazyText_T, text: str
):
    # XXX: We cannot safely compare values from dynamic evaluation of lazy text as
    # prompt toolkit's FormattedText does some kind of magic when translating between
    # ANSI and HTML within to_formatted_text that breaks __hash__ on FormattedText?
    assert isinstance(get_dynamic_value(source, lazy, text), (str, FormattedText))


@given(
    action_group(key_strategy=fragment(min_size=5), max_depth=2, min_size=1, max_size=1)
)
def test_extract_context(group: types.ActionGroup):
    # XXX: This test is a little weak, but it properly tests functionality for ~90% of
    # existing use cases that I can spot just by eyesight

    first_level = list(group.children.keys())[0]
    assert extract_context(group, [first_level[0]]) == (
        None,
        None,
        group,
        [first_level[0]],
    )

    assert extract_context(group, [first_level]) == (
        group,
        first_level,
        group.children[first_level],
        [],
    )

    if isinstance(group.children[first_level], types.Action):
        return

    next_level = list(group.children[first_level].children.keys())[0]  # type: ignore
    assert extract_context(group, [first_level, next_level[0]]) == (
        group,
        first_level,
        group.children[first_level],
        [next_level[0]],
    )

    assert extract_context(group, [first_level, next_level]) == (
        group.children[first_level],
        next_level,
        group.children[first_level].children[next_level],  # type: ignore
        [],
    )

    assert extract_context(group, [first_level, next_level, "test"]) == (
        group.children[first_level],
        next_level,
        group.children[first_level].children[next_level],  # type: ignore
        ["test"],
    )
