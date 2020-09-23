# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains tests related to the custom :class:`~.validator.ActionValidator`."""

from typing import List, Tuple
from unittest.mock import patch

import pytest
from hypothesis import assume, given
from hypothesis.strategies import integers, just, lists, none, one_of, tuples
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.validation import ValidationError, Validator

from action_completer import types
from action_completer.validator import ActionValidator

from .strategies import (
    action,
    action_group,
    action_param,
    action_validator,
    custom_validator_callable,
    fragment,
)


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
    with patch("action_completer.validator.get_best_choice") as mocked_get_best_choice:
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


@given(
    action_validator(just({})),
    action(),
    action_param(
        validators=one_of(
            just([Validator.from_callable(lambda *_: True)]),
            lists(custom_validator_callable(), min_size=1, max_size=1),
        )
    ),
    fragment(),
    lists(fragment(), min_size=1),
    integers(min_value=0),
)
def test_validate_custom_validators(
    validator: ActionValidator,
    action: types.Action,
    action_param: types.ActionParam,
    param_value: str,
    previous_fragments: List[str],
    cursor_position: int,
):
    validator._validate_custom_validators(
        action,
        action_param,
        param_value,
        previous_fragments,
        cursor_position=cursor_position,
    )


@given(
    action_validator(just({})),
    action(),
    action_param(
        validators=lists(
            one_of(
                just(Validator.from_callable(lambda *_: False)),
                custom_validator_callable(fail_validation=True),
            ),
            min_size=1,
        )
    ),
    fragment(),
    lists(fragment(), min_size=1),
    integers(min_value=0),
)
def test_validate_custom_validators_raises_ValidationError_on_failures(
    validator: ActionValidator,
    action: types.Action,
    action_param: types.ActionParam,
    param_value: str,
    previous_fragments: List[str],
    cursor_position: int,
):
    with pytest.raises(ValidationError) as exc_info:
        validator._validate_custom_validators(
            action,
            action_param,
            param_value,
            previous_fragments,
            cursor_position=cursor_position,
        )

    assert exc_info.value.cursor_position == cursor_position


@given(
    action_validator(just({})),
    action(),
    action_param(validators=lists(none(), min_size=1)),
    fragment(),
    lists(fragment(), min_size=1),
    integers(min_value=0),
)
def test_validate_custom_validators_warns_if_unhandled_validator_provided(
    validator: ActionValidator,
    action: types.Action,
    action_param: types.ActionParam,
    param_value: str,
    previous_fragments: List[str],
    cursor_position: int,
):
    with pytest.warns(UserWarning):
        validator._validate_custom_validators(
            action,
            action_param,
            param_value,
            previous_fragments,
            cursor_position=cursor_position,
        )


@given(
    action_validator(just({})),
    action(),
    action_param(source=fragment()),
    fragment(),
    integers(min_value=0),
)
def test_validate_default_validators_handles_basic_params(
    validator: ActionValidator,
    action: types.Action,
    action_param: types.ActionParam,
    param_value: str,
    cursor_position: int,
):
    with patch.object(
        validator, "_validate_basic_param"
    ) as mocked_validate_basic_param:
        validator._validate_default_validators(
            action, action_param, param_value, cursor_position=cursor_position
        )

        mocked_validate_basic_param.assert_called_with(
            action, action_param, param_value, cursor_position=cursor_position
        )


@given(
    action_validator(just({})),
    action(),
    action_param(source=lists(fragment(), min_size=1)),
    fragment(),
    integers(min_value=0),
)
def test_validate_default_validators_handles_iterable_params(
    validator: ActionValidator,
    action: types.Action,
    action_param: types.ActionParam,
    param_value: str,
    cursor_position: int,
):
    with patch.object(
        validator, "_validate_iterable_param"
    ) as mocked_validate_iterable_param:
        validator._validate_default_validators(
            action, action_param, param_value, cursor_position=cursor_position
        )

        mocked_validate_iterable_param.assert_called_with(
            action, action_param, param_value, cursor_position=cursor_position
        )


@given(
    action_validator(just({})),
    action(),
    action_param(source=just(lambda *_: ["test"])),
    fragment(),
    integers(min_value=0),
)
def test_validate_default_validators_handles_callable_params(
    validator: ActionValidator,
    action: types.Action,
    action_param: types.ActionParam,
    param_value: str,
    cursor_position: int,
):
    with patch.object(
        validator, "_validate_callable_param"
    ) as mocked_validate_callable_param:
        validator._validate_default_validators(
            action, action_param, param_value, cursor_position=cursor_position
        )

        mocked_validate_callable_param.assert_called_with(
            action, action_param, param_value, cursor_position=cursor_position
        )


@given(action_validator(just({})), action(), action_param(source=integers()))
def test_validate_default_validators_skips_validation_on_unsupported_param_source(
    validator: ActionValidator, action: types.Action, action_param: types.ActionParam
):
    assert validator._validate_default_validators(action, action_param, "") is None


@given(
    action_validator(just({})),
    action(
        params=lists(
            action_param(
                validators=lists(
                    one_of(
                        just(Validator.from_callable(lambda *_: True)),
                        custom_validator_callable(),
                    ),
                    min_size=1,
                )
            ),
            min_size=1,
            max_size=1,
        )
    ),
    lists(fragment(), min_size=1, max_size=1),
    fragment(),
)
def test_validate_action(
    validator: ActionValidator,
    action: types.Action,
    fragments: List[str],
    parent_name: str,
):
    validator._validate_action(action, fragments, parent_name)


@given(
    action_validator(just({})),
    action(
        params=lists(
            action_param(
                validators=lists(
                    one_of(
                        just(Validator.from_callable(lambda *_: False)),
                        custom_validator_callable(fail_validation=True),
                    ),
                    min_size=1,
                )
            ),
            min_size=1,
        )
    ),
    lists(fragment(), min_size=1, max_size=1),
    fragment(),
    integers(min_value=0),
)
def test_validator_action_raises_ValidationError_on_failures(
    validator: ActionValidator,
    action: types.Action,
    fragments: List[str],
    parent_name: str,
    cursor_position: int,
):
    with pytest.raises(ValidationError) as exc_info:
        validator._validate_action(
            action, fragments, parent_name, cursor_position=cursor_position
        )

    assert exc_info.value.cursor_position == cursor_position
    # TODO: message verification
    assert isinstance(exc_info.value.message, str)


@given(
    action_validator(just({})),
    action(params=one_of(none(), lists(none(), max_size=0))),
    lists(fragment(), min_size=1),
    fragment(),
)
def test_validate_action_skips_validation_if_missing_params(
    validator: ActionValidator,
    action: types.Action,
    fragments: List[str],
    parent_name: str,
):
    assert validator._validate_action(action, fragments, parent_name) is None


@given(
    action_validator(just({})),
    action(params=lists(action_param(source=fragment()), min_size=1)),
    fragment(),
    integers(min_value=0),
)
def test_validate_action_raises_ValidationError_on_invalid_number_of_parameters(
    validator: ActionValidator,
    action: types.Action,
    parent_name: str,
    cursor_position: int,
):
    with pytest.raises(ValidationError) as exc_info:
        fragments = [param.source for param in action.params]  # type: ignore
        for invalid_fragments in (fragments[:-1], fragments + [parent_name]):
            validator._validate_action(
                action,
                invalid_fragments,  # type: ignore
                parent_name,
                cursor_position=cursor_position,
            )

    assert exc_info.value.cursor_position == cursor_position
    assert exc_info.value.message.startswith(
        f"Invalid number of parameters for {parent_name!r}"
    )


@given(
    action_validator(just({})),
    action(
        params=lists(action_param(source=fragment()), min_size=1),
        capture_all=just(True),
    ),
    fragment(),
)
def test_validate_action_raises_ValidationError_for_capture_all(
    validator: ActionValidator,
    action: types.Action,
    parent_name: str,
):
    with pytest.raises(ValidationError) as exc_info:
        fragments = [param.source for param in action.params]  # type: ignore
        validator._validate_action(
            action,
            fragments[:-1],  # type: ignore
            parent_name,
        )

    validator._validate_action(
        action,
        fragments + [parent_name],  # type: ignore
        parent_name,
    )


@given(
    action_validator(just({})),
    action_group(),
    fragment(),
    lists(fragment(), min_size=1),
    integers(max_value=0),
)
def test_validate_handles_group(
    validator: ActionValidator,
    group: types.ActionGroup,
    parent_name: str,
    fragments: List[str],
    cursor_position: int,
):
    with patch(
        "action_completer.validator.extract_context"
    ) as mocked_extract_context, patch.object(
        validator, "_validate_group"
    ) as mocked_validate_group:
        mocked_extract_context.return_value = (None, parent_name, group, fragments)

        validator.validate(Document(text="", cursor_position=cursor_position))
        mocked_validate_group.assert_called_with(
            group, fragments, parent_name, cursor_position=cursor_position
        )


@given(
    action_validator(just({})),
    action_group(),
    action(),
    fragment(),
    lists(fragment(), min_size=1),
    integers(max_value=0),
)
def test_validate_handles_action(
    validator: ActionValidator,
    group: types.ActionGroup,
    action: types.Action,
    parent_name: str,
    fragments: List[str],
    cursor_position: int,
):
    with patch(
        "action_completer.validator.extract_context"
    ) as mocked_extract_context, patch.object(
        validator, "_validate_action"
    ) as mocked_validate_action:
        mocked_extract_context.return_value = (group, parent_name, action, fragments)

        validator.validate(Document(text="", cursor_position=cursor_position))
        mocked_validate_action.assert_called_with(
            action, fragments, parent_name, cursor_position=cursor_position
        )


@given(
    action_validator(just({})),
    action_group(),
    action(active=just(Condition(lambda *_: False))),
    fragment(),
    lists(fragment(), min_size=1),
    integers(max_value=0),
)
def test_validate_handles_parent_group_if_action_is_inactive(
    validator: ActionValidator,
    group: types.ActionGroup,
    action: types.Action,
    parent_name: str,
    fragments: List[str],
    cursor_position: int,
):
    with patch(
        "action_completer.validator.extract_context"
    ) as mocked_extract_context, patch.object(
        validator, "_validate_group"
    ) as mocked_validate_group:
        mocked_extract_context.return_value = (group, parent_name, action, fragments)

        validator.validate(Document(text="", cursor_position=cursor_position))
        mocked_validate_group.assert_called_with(
            group, fragments, parent_name, cursor_position=cursor_position
        )


@given(
    action_validator(just({})),
    action_group(),
    action(),
    fragment(),
    lists(fragment(), min_size=1),
)
def test_validate_skips_validation_if_unhandled_context(
    validator: ActionValidator,
    group: types.ActionGroup,
    action: types.Action,
    parent_name: str,
    fragments: List[str],
):
    with patch("action_completer.validator.extract_context") as mocked_extract_context:
        mocked_extract_context.return_value = (group, parent_name, None, fragments)

        assert validator.validate(Document(text="")) is None

    with patch("action_completer.validator.extract_context") as mocked_extract_context:
        mocked_extract_context.return_value = (group, None, action, fragments)

        assert validator.validate(Document(text="")) is None
