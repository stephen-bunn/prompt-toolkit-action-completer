# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains tests related to the custom :class:`~.validator.ActionValidator`."""

from typing import List, Tuple
from unittest.mock import patch

import pytest
from hypothesis import assume, given
from hypothesis.strategies import integers, just, lists, one_of, tuples
from prompt_toolkit.filters import Condition
from prompt_toolkit.validation import ValidationError

from action_completer import types
from action_completer.validator import ActionValidator

from .strategies import action, action_group, action_param, action_validator, fragment


@given(action_validator(just({})), lists(fragment(), min_size=1))
def test_get_best_choice(validator: ActionValidator, choices: List[str]):
    assert validator._get_best_choice(choices, choices[0]) == choices[0]


@given(action_validator(just({})), lists(fragment(), min_size=1), fragment())
def test_get_best_choice_returns_None_if_no_best_choice(
    validator: ActionValidator, choices: List[str], text: str
):
    with patch("action_completer.validator.fuzzy_process") as mocked_fuzzy_process:
        mocked_fuzzy_process.extractOne.return_value = []

        assert validator._get_best_choice(choices, text) is None


@given(
    action_validator(just({})),
    one_of(
        tuples(just([]), fragment()), tuples(lists(fragment(), min_size=1), just(""))
    ),
)
def test_validate_choices_skips_validation_if_missing_choices_or_text(
    validator: ActionValidator, choices_text_pair: Tuple[List[str], str]
):
    choices, text = choices_text_pair
    assert validator._validate_choices(choices, text) is None


@given(action_validator(just({})), lists(fragment(), min_size=1))
def test_validate_choices(validator: ActionValidator, choices: List[str]):
    assert validator._validate_choices(choices, choices[0]) is None


@given(
    action_validator(just({})),
    lists(fragment(), min_size=1, max_size=1),
    fragment(),
    integers(min_value=0),
)
def test_validate_choices_raises_ValidationError_with_text_if_one_choice_available(
    validator: ActionValidator, choices: List[str], text: str, cursor_position: int
):
    assume(text not in choices)
    with pytest.raises(ValidationError) as exc_info:
        validator._validate_choices(choices, text, cursor_position=cursor_position)

    assert exc_info.value.cursor_position == cursor_position
    assert exc_info.value.message == f"Invalid value {text!r}, expected {choices[0]!r}"


@given(
    action_validator(just({})),
    lists(fragment(), min_size=2),
    fragment(),
    integers(min_value=0),
)
def test_validate_choices_raises_ValidationError_with_closest_choice(
    validator: ActionValidator, choices: List[str], text: str, cursor_position: int
):
    assume(text not in choices)
    with pytest.raises(ValidationError) as exc_info:
        validator._validate_choices(choices, text, cursor_position=cursor_position)

    assert exc_info.value.cursor_position == cursor_position
    assert exc_info.value.message.startswith(f"Invalid value {text!r}, did you mean")


@given(
    action_validator(just({})),
    lists(fragment(), min_size=2),
    fragment(),
    integers(min_value=0),
)
def test_validate_choices_raises_ValidationError_without_closest_choice(
    validator: ActionValidator, choices: List[str], text: str, cursor_position: int
):
    assume(text not in choices)
    with patch.object(validator, "_get_best_choice") as mocked_get_best_choice:
        mocked_get_best_choice.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            validator._validate_choices(choices, text, cursor_position=cursor_position)

        assert exc_info.value.cursor_position == cursor_position
        assert exc_info.value.message == f"Invalid value {text!r}"


@given(
    action_validator(just({})),
    action_group(min_size=1),
    lists(fragment(), min_size=1),
    integers(min_value=0),
)
def test_validate_group(
    validator: ActionValidator,
    group: types.ActionGroup,
    fragments: List[str],
    cursor_position: int,
):
    with patch.object(validator, "_validate_choices") as mocked_validate_choices:
        validator._validate_group(group, fragments, cursor_position=cursor_position)

        mocked_validate_choices.assert_called_with(
            list(group.children.keys()), fragments[-1], cursor_position=cursor_position
        )


@given(
    action_validator(just({})),
    action_group(
        action_strategy=action(active=just(Condition(lambda *_: False))), max_depth=0
    ),
    lists(fragment(), min_size=1),
    integers(min_value=0),
)
def test_validate_group_skips_validation_if_no_available_choices(
    validator: ActionValidator,
    group: types.ActionGroup,
    fragments: List[str],
    cursor_position: int,
):
    assert (
        validator._validate_group(group, fragments, cursor_position=cursor_position)
        is None
    )


@given(action_validator(just({})), action_group(), just([]))
def test_validate_group_skips_validation_if_missing_fragments(
    validator: ActionValidator,
    group: types.ActionGroup,
    fragments: List[str],
):
    assert validator._validate_group(group, fragments) is None


@given(
    action_validator(just({})),
    action(),
    action_param(source=fragment()),
    fragment(),
)
def test_validate_basic_param(
    validator: ActionValidator,
    action: types.Action,
    action_param: types.ActionParam,
    param_value: str,
):
    assume(param_value != action_param.source)
    validator._validate_basic_param(
        action, action_param, action_param.source  # type: ignore
    )

    with pytest.raises(ValidationError):
        validator._validate_basic_param(action, action_param, param_value)


@given(
    action_validator(just({})),
    action(),
    action_param(source=lists(fragment(), min_size=2)),
    fragment(),
)
def test_validate_iterable_param(
    validator: ActionValidator,
    action: types.Action,
    action_param: types.ActionParam,
    param_value: str,
):
    assume(param_value not in action_param.source)  # type: ignore
    validator._validate_iterable_param(
        action, action_param, action_param.source[0]  # type: ignore
    )

    with pytest.raises(ValidationError):
        validator._validate_iterable_param(action, action_param, param_value)


@given(
    action_validator(just({})),
    action(),
    action_param(source=just(lambda *_: ["test"])),
    fragment(),
)
def test_validate_callable_param(
    validator: ActionValidator,
    action: types.Action,
    action_param: types.ActionParam,
    param_value: str,
):
    assume(param_value != "test")
    validator._validate_callable_param(action, action_param, "test")

    with pytest.raises(ValidationError):
        validator._validate_callable_param(action, action_param, param_value)
