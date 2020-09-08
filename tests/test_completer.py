# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""
"""

from string import printable
from typing import List, Optional
from unittest.mock import patch

import pytest
from hypothesis import assume, given
from hypothesis.strategies import (
    builds,
    integers,
    just,
    lists,
    none,
    nothing,
    one_of,
    text,
)
from prompt_toolkit.completion import CompleteEvent, Completion
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import FormattedText

from action_completer import types
from action_completer.completer import ActionCompleter
from action_completer.utils import noop

from .strategies import (
    action,
    action_completable,
    action_completer,
    action_group,
    action_param,
    fragment,
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
        action_completable(style=just(noop)),
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
        action_completable(selected_style=just(noop)),
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
