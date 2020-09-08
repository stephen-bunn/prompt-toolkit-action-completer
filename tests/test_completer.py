# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains tests related to the custom :class:`~.completer.ActionCompleter`."""

from string import ascii_letters, digits, printable
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import assume, given
from hypothesis.strategies import (
    builds,
    dictionaries,
    integers,
    just,
    lists,
    none,
    nothing,
    one_of,
    sampled_from,
    text,
)
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import FormattedText

from action_completer import types, utils
from action_completer.completer import ActionCompleter
from action_completer.validator import ActionValidator

from .strategies import (
    action,
    action_completable,
    action_completer,
    action_group,
    action_param,
    builtin_types,
    fragment,
    generic_completer,
    lazy_string,
    lazy_text,
)


def test_ActionCompleter_defaults_to_empty_root():
    completer = ActionCompleter()
    assert completer.root == types.ActionGroup({})


@given(lazy_string(), lazy_text(allow_none=False))
def test_ActionCompleter_warns_if_root_contains_display_properties(
    lazy_string: types.LazyString_T, lazy_text: types.LazyText_T
):
    for test_value, properties in zip(
        (lazy_string, lazy_text),
        (("style", "selected_style"), ("display", "display_meta")),
    ):
        for property_name in properties:
            with pytest.warns(UserWarning):
                ActionCompleter(
                    root=types.ActionGroup({}, **{property_name: test_value})
                )


@given(action_completer(just({})), text(alphabet=printable, min_size=1))
def test_compare_string(completer: ActionCompleter, full_string: str):
    assert completer._compare_string(full_string, full_string) is True
    assert completer._compare_string(full_string[0], full_string) is True

    assume("test" not in full_string)
    assert completer._compare_string("test", full_string) is False


@given(
    action_completer(just({})),
    action_completable(style=lazy_string(value_strategy=just("test"))),
    text(alphabet=printable, min_size=1),
)
def test_get_completion_style(
    completer: ActionCompleter, completable: types.ActionCompletable_T, text: str
):
    assert completer._get_completion_style(completable, text) == "test"


@given(
    action_completer(just({})),
    action_completable(),
    text(alphabet=printable, min_size=1),
    text(alphabet=printable, min_size=1),
)
def test_get_completion_style_returns_override_when_provided(
    completer: ActionCompleter,
    completable: types.ActionCompletable_T,
    text: str,
    default: str,
):
    assert completer._get_completion_style(completable, text, default) == default


@given(
    action_completer(just({})),
    one_of(
        action_completable(style=none()),
        action_completable(style=just(utils.noop)),
    ),
    text(alphabet=printable, min_size=1),
)
def test_get_completion_style_returns_blank_string_when_necessary(
    completer: ActionCompleter, completable: types.ActionCompletable_T, text: str
):
    assert completer._get_completion_style(completable, text) == ""


@given(
    action_completer(just({})),
    action_completable(selected_style=lazy_string(value_strategy=just("test"))),
    text(alphabet=printable, min_size=1),
)
def test_get_completion_selected_style(
    completer: ActionCompleter, completable: types.ActionCompletable_T, text: str
):
    assert completer._get_completion_selected_style(completable, text) == "test"


@given(
    action_completer(just({})),
    action_completable(),
    text(alphabet=printable, min_size=1),
    text(alphabet=printable, min_size=1),
)
def test_get_completion_selected_style_returns_override_when_provided(
    completer: ActionCompleter,
    completable: types.ActionCompletable_T,
    text: str,
    default: str,
):
    assert (
        completer._get_completion_selected_style(completable, text, default) == default
    )


@given(
    action_completer(just({})),
    one_of(
        action_completable(selected_style=none()),
        action_completable(selected_style=just(utils.noop)),
    ),
    text(alphabet=printable, min_size=1),
)
def test_get_completion_selected_style_returns_blank_string_when_necessary(
    completer: ActionCompleter, completable: types.ActionCompletable_T, text: str
):
    assert completer._get_completion_selected_style(completable, text) == ""


@given(
    action_completer(just({})),
    action_completable(
        display=lazy_text(value_strategy=just("test"), allow_none=False)
    ),
    text(alphabet=printable, min_size=1),
)
def test_get_completion_display(
    completer: ActionCompleter, completable: types.ActionCompletable_T, text: str
):
    assert completer._get_completion_display(completable, text) == "test"


@given(
    action_completer(just({})),
    action_completable(),
    text(alphabet=printable, min_size=1),
    lazy_text(value_strategy=just("test"), allow_none=False),
)
def test_get_completion_display_returns_override_when_provided(
    completer: ActionCompleter,
    completable: types.ActionCompletable_T,
    text: str,
    override: str,
):
    assert completer._get_completion_display(completable, text, override) == "test"


@given(
    action_completer(just({})),
    action_completable(display=none()),
    text(alphabet=printable, min_size=1),
)
def test_get_completion_display_returns_None_when_necessary(
    completer: ActionCompleter, completable: types.ActionCompletable_T, text: str
):
    assert completer._get_completion_display(completable, text) is None


@given(
    action_completer(just({})),
    action_completable(
        display_meta=lazy_text(value_strategy=just("test"), allow_none=False)
    ),
    text(alphabet=printable, min_size=1),
)
def test_get_completion_display_meta(
    completer: ActionCompleter, completable: types.ActionCompletable_T, text: str
):
    assert completer._get_completion_display_meta(completable, text) == "test"


@given(
    action_completer(just({})),
    one_of(
        action_completable(display_meta=none()),
        action_completable(display_meta=lazy_text(value_strategy=just("test"))),
    ),
    text(alphabet=printable, min_size=1),
    lazy_text(value_strategy=just("test"), allow_none=False),
)
def test_get_completion_display_meta_returns_override_when_provided(
    completer: ActionCompleter,
    completable: types.ActionCompletable_T,
    text: str,
    override: str,
):
    assert completer._get_completion_display_meta(completable, text, override) == "test"


@given(
    action_completer(just({})),
    action_completable(),
    text(alphabet=printable, min_size=1),
    lazy_text(value_strategy=none(), allow_none=False),
)
def test_get_completion_display_meta_failed_override_falls_back_to_empty_string(
    completer: ActionCompleter,
    completable: types.ActionCompletable_T,
    text: str,
    override: types.LazyText_T,
):
    assert completer._get_completion_display_meta(completable, text, override) == ""


@given(
    action_completer(just({})),
    one_of(
        action_completable(display_meta=none()),
        action_completable(display_meta=lazy_text(value_strategy=none())),
    ),
    text(alphabet=printable, min_size=1),
)
def test_get_completion_display_meta_returns_empty_string_when_necessary(
    completer: ActionCompleter,
    completable: types.ActionCompletable_T,
    text: str,
):
    assert completer._get_completion_display_meta(completable, text) == ""


@given(
    action_completer(just({})),
    action_completable(
        style=lazy_string(value_strategy=just("test style")),
        selected_style=lazy_string(value_strategy=just("test selected_style")),
        display=lazy_text(allow_none=False),
        display_meta=lazy_text(allow_none=False),
    ),
    text(alphabet=printable, min_size=1),
    integers(max_value=0),
)
def test_get_completion(
    completer: ActionCompleter,
    completable: types.ActionCompletable_T,
    text: str,
    start_position: int,
):
    completion = completer._build_completion(
        completable, text, start_position=start_position
    )

    assert completion.text == text
    assert completion.start_position == start_position
    assert completion.style == "test style"
    assert completion.selected_style == "test selected_style"

    # XXX: Due to how prompt_toolkit's FormattedText has no clean method of extracting
    # the raw text from a FormattedText instance, we are JUST checking types here, not
    # content as I would like to
    assert isinstance(completion.display, (str, FormattedText))
    assert isinstance(completion.display_meta, (str, FormattedText))


@given(
    action_completer(just({})),
    action_group(key_strategy=just("test"), min_size=1, max_size=1, max_depth=1),
    lists(fragment(), min_size=1),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_group_completions(
    completer: ActionCompleter,
    group: types.ActionGroup,
    fragments: List[str],
    complete_event: CompleteEvent,
    start_position: int,
):
    with patch.object(
        completer, "_build_completion", wraps=completer._build_completion
    ) as mock_build_completion:
        for completion in list(
            completer._iter_group_completions(
                group, fragments, complete_event, start_position=start_position
            )
        ):
            assert isinstance(completion, Completion)
            assert completion.start_position == start_position

            for child in group.children.values():
                mock_build_completion.assert_called_with(
                    completable=child,
                    text="test",
                    start_position=start_position,
                )


@given(
    action_completer(just({})),
    action_group(
        action_strategy=action(active=just(Condition(lambda *_: False))),
        active=just(Condition(lambda *_: False)),
    ),
    lists(fragment(), min_size=1),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_group_completions_skips_inactive_sources(
    completer: ActionCompleter,
    group: types.ActionGroup,
    fragments: List[str],
    complete_event: CompleteEvent,
    start_position: int,
):
    assert (
        len(
            list(
                completer._iter_group_completions(
                    group, fragments, complete_event, start_position=start_position
                )
            )
        )
        == 0
    )


@given(
    action_completer(just({})),
    action(),
    action_param(source=text(alphabet=printable, min_size=1)),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_basic_param_completions(
    completer: ActionCompleter,
    action: types.Action,
    action_param: types.ActionParam,
    complete_event: CompleteEvent,
    start_position: int,
):
    completions = list(
        completer._iter_basic_param_completions(
            action,
            action_param,
            action_param.source,  # type: ignore
            complete_event,
            start_position=start_position,
        )
    )
    assert len(completions) == 1

    first_completion, *_ = completions
    assert first_completion.text == action_param.source
    assert first_completion.start_position == start_position


@given(
    action_completer(just({})),
    action(),
    action_param(source=just("test")),
    just("invalid"),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_basic_param_completions_invalid_value(
    completer: ActionCompleter,
    action: types.Action,
    action_param: types.ActionParam,
    param_value: str,
    complete_event: CompleteEvent,
    start_position: int,
):
    assert (
        len(
            list(
                completer._iter_basic_param_completions(
                    action,
                    action_param,
                    param_value,
                    complete_event,
                    start_position=start_position,
                )
            )
        )
        == 0
    )


@given(
    action_completer(just({})),
    action(),
    action_param(source=lists(fragment(), min_size=1, unique=True)),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_iterable_param_completions(
    completer: ActionCompleter,
    action: types.Action,
    action_param: types.ActionParam,
    complete_event: CompleteEvent,
    start_position: int,
):
    completions = list(
        completer._iter_iterable_param_completions(
            action, action_param, "", complete_event, start_position=start_position
        )
    )
    assert len(completions) == len(action_param.source)  # type: ignore

    for completion, source in zip(completions, action_param.source):  # type: ignore
        assert completion.text == source
        assert completion.start_position == start_position


@given(
    action_completer(just({})),
    action(),
    action_param(source=just(["foo", "bar"])),
    sampled_from(["fo", "foo"]),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_iterable_param_completions_partial_text(
    completer: ActionCompleter,
    action: types.Action,
    action_param: types.ActionParam,
    param_value: str,
    complete_event: CompleteEvent,
    start_position: int,
):
    completions = list(
        completer._iter_iterable_param_completions(
            action,
            action_param,
            param_value,
            complete_event,
            start_position=start_position,
        )
    )
    assert len(completions) == 1

    first_completion, *_ = completions
    assert first_completion.text == "foo"
    assert first_completion.start_position == start_position


@given(
    action_completer(just({})),
    action(),
    action_param(source=generic_completer()),
    builds(CompleteEvent),
)
def test_iter_completer_param_completions(
    completer: ActionCompleter,
    action: types.Action,
    action_param: types.ActionParam,
    complete_event: CompleteEvent,
):

    completions = list(
        completer._iter_completer_param_completions(
            action, action_param, "test", complete_event
        )
    )
    assert len(completions) == 1

    first_completion, *_ = completions
    assert first_completion.text == "test"
    assert (
        isinstance(first_completion.start_position, int)
        and first_completion.start_position <= 0
    )


@given(
    action_completer(just({})),
    action(),
    action_param(source=just(lambda *_: ["foo", "bar"])),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_callable_param_completions(
    completer: ActionCompleter,
    action: types.Action,
    action_param: types.ActionParam,
    complete_event: CompleteEvent,
    start_position: int,
):
    completions = list(
        completer._iter_callable_param_completions(
            action, action_param, "fo", complete_event, start_position=start_position
        )
    )
    assert len(completions) == 1

    first_completion, *_ = completions
    assert first_completion.text == "foo"
    assert first_completion.start_position == start_position


@given(
    action_completer(just({})),
    action(),
    action_param(source=none()),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_none_param_completions(
    completer: ActionCompleter,
    action: types.Action,
    action_param: types.ActionParam,
    complete_event: CompleteEvent,
    start_position: int,
):
    assert (
        len(
            list(
                completer._iter_none_param_completions(
                    action,
                    action_param,
                    "test",
                    complete_event,
                    start_position=start_position,
                )
            )
        )
        == 0
    )


@given(
    action_completer(just({})),
    action(),
    action_param(
        source=none(),
        display=lazy_text(allow_none=False),
        display_meta=lazy_text(allow_none=False),
    ),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_none_param_completions_yields_if_display_or_display_meta_provided(
    completer: ActionCompleter,
    action: types.Action,
    action_param: types.ActionParam,
    complete_event: CompleteEvent,
    start_position: int,
):
    completions = list(
        completer._iter_none_param_completions(
            action, action_param, "test", complete_event, start_position=start_position
        )
    )

    assert len(completions) == 1

    first_completion, *_ = completions
    assert first_completion.text == "test"


@given(
    action_completer(just({})),
    action(
        params=lists(
            action_param(
                source=one_of(
                    fragment(),
                    lists(fragment(), min_size=1, unique=True),
                    generic_completer(),
                    just(lambda *_: ["test"]),
                )
            ),
            min_size=1,
        )
    ),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_action_completions(
    completer: ActionCompleter,
    action: types.Action,
    complete_event: CompleteEvent,
    start_position: int,
):
    completions = completer._iter_action_completions(
        action, [""], complete_event, start_position=start_position
    )
    assert len(list(completions)) > 0
    assert all(
        completion.start_position == start_position for completion in completions
    )


@given(
    action_completer(just({})),
    action(
        params=one_of(none(), just([]), lists(action_param(source=none()), max_size=1))
    ),
    lists(fragment(), min_size=1),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_action_completions_does_not_yield_if_no_completable_parameters_provided(
    completer: ActionCompleter,
    action: types.Action,
    fragments: List[str],
    complete_event: CompleteEvent,
    start_position: int,
):
    completions = completer._iter_action_completions(
        action, fragments, complete_event, start_position=start_position
    )
    assert len(list(completions)) == 0


@given(
    action_completer(just({})),
    action(params=lists(action_param(source=integers()), max_size=1)),
    lists(fragment(), min_size=1),
    builds(CompleteEvent),
    integers(max_value=0),
)
def test_iter_action_completions_does_not_yield_if_no_source_completion_iterator(
    completer: ActionCompleter,
    action: types.Action,
    fragments: List[str],
    complete_event: CompleteEvent,
    start_position: int,
):

    # XXX: this test is dependent that we don't ever attempt to complete for integers as
    # a parameter source in the future
    completions = completer._iter_action_completions(
        action, fragments, complete_event, start_position=start_position
    )
    assert len(list(completions)) == 0


@given(
    action_completer(
        action_group(
            action_strategy=action_group(),
            min_size=1,
            max_size=1,
            max_depth=0,
        ),
    ),
    builds(CompleteEvent),
)
def test_get_completions_yields_for_ActionGroup_completable(
    completer: ActionCompleter, complete_event: CompleteEvent
):
    completions = completer.get_completions(Document(), complete_event)
    assert len(list(completions)) > 0


@given(
    action_completer(
        action_group(
            action_strategy=action(
                params=lists(action_param(source=fragment()), min_size=1)
            ),
            min_size=1,
            max_size=1,
            max_depth=0,
        ),
    ),
    builds(CompleteEvent),
)
def test_get_completions_yields_for_Action_completable(
    completer: ActionCompleter, complete_event: CompleteEvent
):
    first_key = list(completer.root.children.keys())[0]
    completions = completer.get_completions(
        Document(text=f"{first_key!s} "), complete_event
    )
    assert len(list(completions)) > 0


@given(action_completer(), builds(CompleteEvent))
def test_get_completions_does_not_yield_if_no_fragments_extracted(
    completer: ActionCompleter, complete_event: CompleteEvent
):
    with patch("action_completer.completer.get_fragments") as mocked_get_fragments:
        mocked_get_fragments.return_value = []

        completions = completer.get_completions(Document(), complete_event)
        assert len(list(completions)) == 0


@given(action_completer(), builds(CompleteEvent))
def test_get_completions_does_not_yield_if_no_completable_completion_iterator(
    completer: ActionCompleter, complete_event: CompleteEvent
):
    with patch("action_completer.completer.extract_context") as mocked_extract_context:
        # fragments here must be a list of some string in order to skip the first early
        # return from the get_completions generator
        mocked_extract_context.return_value = (None, None, None, [""])

        completions = completer.get_completions(Document(), complete_event)
        assert len(list(completions)) == 0


@given(action_completer())
def test_get_validator(completer: ActionCompleter):
    validator = completer.get_validator()
    assert isinstance(validator, ActionValidator)
    assert validator.root == completer.root


@given(
    action_completer(just({})),
    action(params=lists(action_param(source=fragment()), min_size=1)),
)
def test_iter_partial_action_parameters(
    completer: ActionCompleter, action: types.Action
):
    targets = [param.source for param in action.params]  # type: ignore
    for source, target in zip(
        completer._iter_partial_action_parameters(action, targets),  # type: ignore
        targets,
    ):
        assert source == target


@given(
    action_completer(just({})),
    action(
        params=lists(
            action_param(source=text(alphabet=digits, min_size=1), cast=just(int)),
            min_size=1,
        )
    ),
)
def test_iter_partial_action_parameters_applies_cast_if_present(
    completer: ActionCompleter, action: types.Action
):
    assert all(
        isinstance(value, int)
        for value in completer._iter_partial_action_parameters(
            action, [param.source for param in action.params]  # type: ignore
        )
    )


@given(
    action_completer(just({})),
    action(params=one_of(none(), just([]))),
    lists(fragment(), min_size=1),
)
def test_iter_partial_action_parameters_does_not_yield_for_empty_params(
    completer: ActionCompleter, action: types.Action, fragments: List[str]
):
    action_parameters = completer._iter_partial_action_parameters(action, fragments)
    assert len(list(action_parameters)) == 0


@given(action_completer(just({})), action(), just([]))
def test_iter_partial_action_parameters_does_not_yield_for_empty_fragments(
    completer: ActionCompleter, action: types.Action, fragments: List[str]
):
    action_parameters = completer._iter_partial_action_parameters(action, fragments)
    assert len(list(action_parameters)) == 0


@given(
    action_completer(just({})),
    action(
        params=lists(action_param(source=fragment()), min_size=1, max_size=1),
        capture_all=just(True),
    ),
    lists(fragment(), min_size=1),
)
def test_iter_partial_action_parameters_captures_trailing_fragments_if_capture_all(
    completer: ActionCompleter, action: types.Action, fragments: List[str]
):
    action_parameters = completer._iter_partial_action_parameters(action, fragments)
    assert list(action_parameters) == fragments


@given(
    action_completer(just({})),
    action(
        action=just(utils.noop),
        params=lists(action_param(source=fragment()), min_size=1),
    ),
)
def test_get_partial_action(completer: ActionCompleter, action: types.Action):
    with patch("action_completer.completer.extract_context") as mocked_extract_context:
        targets = [param.source for param in action.params]  # type: ignore
        mocked_extract_context.return_value = (None, None, action, targets)

        partial_action = completer.get_partial_action("")
        assert partial_action.func == utils.noop  # type: ignore
        assert partial_action.args == tuple(targets)  # type: ignore


@given(
    action_completer(just({})),
    one_of(action_group(), builtin_types()),
    lists(fragment(), min_size=1),
)
def test_get_partial_action_raises_ValueError_if_extracted_completable_is_not_Action(
    completer: ActionCompleter, group: types.ActionGroup, fragments: List[str]
):
    with patch("action_completer.completer.extract_context") as mocked_extract_context:
        mocked_extract_context.return_value = (None, None, group, fragments)

        with pytest.raises(ValueError):
            completer.get_partial_action("")


@given(action_completer(just({})), action(action=none()), lists(fragment(), min_size=1))
def test_get_partial_action_defaults_to_noop_if_Action_missing_callable(
    completer: ActionCompleter, action: types.Action, fragments: List[str]
):
    with patch("action_completer.completer.extract_context") as mocked_extract_context:
        mocked_extract_context.return_value = (None, None, action, fragments)

        partial_action = completer.get_partial_action("")
        assert partial_action.func == utils.noop  # type: ignore


@given(
    action_completer(just({})),
    lists(builtin_types()),
    dictionaries(text(alphabet=printable), builtin_types()),
)
def test_run_action(
    completer: ActionCompleter, args: List[Any], kwargs: Dict[str, Any]
):
    with patch.object(completer, "get_partial_action") as mocked_get_partial_action:
        mocked_get_partial_action.return_value = MagicMock()

        completer.run_action("", *args, **kwargs)
        mocked_get_partial_action.return_value.assert_called_with(*args, **kwargs)
