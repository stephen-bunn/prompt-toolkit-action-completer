# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains tests related to the functionality provided in the utilities."""

import re
from string import ascii_letters, digits, printable, punctuation
from typing import Any, List, Optional, Type, Union
from unittest.mock import patch

import pytest
from fuzzywuzzy import process as fuzzy_process
from hypothesis import assume, given
from hypothesis.strategies import just, lists, none, one_of, sampled_from, text
from prompt_toolkit.formatted_text import FormattedText

from action_completer import types
from action_completer.utils import (
    decode_completion,
    encode_completion,
    extract_context,
    format_dynamic_value,
    get_best_choice,
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


@given(lists(fragment(), min_size=2, unique=True))
def test_get_best_choice(choices: List[str]):
    assert get_best_choice(choices, choices[0]) == choices[0]


@given(just([]), fragment())
def test_get_best_choices_returns_None_if_no_choices(choices: List[str], text: str):
    assert get_best_choice(choices, text) is None


@given(lists(fragment(), min_size=1, max_size=1), fragment())
def test_get_best_choices_returns_only_available_choice(choices: List[str], text: str):
    assert get_best_choice(choices, choices[0]) == choices[0]


@given(lists(fragment(alphabet=ascii_letters + digits), min_size=2, unique=True))
def test_get_best_choice_returns_None_if_no_best_choice(choices: List[str]):
    with patch("action_completer.utils.fuzzy_process") as mocked_fuzzy_process:
        mocked_fuzzy_process.extractOne.return_value = []

        assert get_best_choice(choices, choices[0]) is None


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
    lists(text(alphabet=ascii_letters + digits, min_size=1), min_size=1, unique=True),
    text(alphabet=punctuation.replace("_", ""), min_size=1),
)
def test_iter_best_choices_does_not_raise_warnings_with_punctuation(
    choices: List[str], user_value: str
):
    # NOTE: fuzzywuzzy doesn't consider _ (underscore) to be punctuation
    with pytest.warns(None) as warning_record:
        assert list(iter_best_choices(choices, user_value)) == choices

    assert len(warning_record) == 0


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


@given(just("{completion}"), text(alphabet=printable))
def test_format_dynamic_value(template: str, text: str):
    assert format_dynamic_value(template, text) == text


@given(sampled_from(["{", "}", "{}", "{c", "{completer"]), text(alphabet=printable))
def test_format_dynamic_value_allows_partial_formats(template: str, text):
    assert format_dynamic_value(template, text) == template


@given(
    one_of(action_param(), action(), action_group()),
    just("{completion}"),
    text(alphabet=printable),
)
def test_get_dynamic_value_LazyText_formats_completion_text_str(
    source: types.ActionCompletable_T, lazy: types.LazyText_T, text: str
):
    assert get_dynamic_value(source, lazy, text) == text


@given(
    one_of(action_param(), action(), action_group()),
    just(FormattedText([("", "{completion}")])),
    text(alphabet=printable),
)
def test_get_dynamic_value_LazyText_formats_completion_text_FormattedText(
    source: types.ActionCompletable_T, lazy: types.LazyText_T, text: str
):
    assert get_dynamic_value(source, lazy, text) == FormattedText([("", text)])


@given(
    one_of(action_param(), action(), action_group()),
    builtin_types(exclude=[str]),
    text(alphabet=printable),
    builtin_types(),
)
def test_get_dynamic_value_LazyText_returns_default(
    source: types.ActionCompletable_T, lazy: Any, text: str, default: Any
):
    assert get_dynamic_value(source, lazy, text, default=default) is default


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
