# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains tests regarded to the functionality provided in types."""


from string import whitespace
from typing import List

import pytest
from hypothesis import assume, given
from hypothesis.strategies import builds, lists, one_of, text

from action_completer import types, utils

from .strategies import action, action_group, action_param, fragment


@given(one_of(text(max_size=0), text(alphabet=whitespace)))
def test_ActionGroup_validates_children(invalid_key: str):
    with pytest.raises(ValueError):
        types.ActionGroup(children={invalid_key: types.Action()})


@given(action_group(), fragment())
def test_ActionGroup_group_creates_subgroups(group: types.ActionGroup, group_name: str):
    assume(group_name not in group.children)
    subgroup = group.group(group_name)

    assert group_name in group.children
    assert group.children[group_name] == subgroup


@given(action_group(), text(max_size=0))
def test_ActionGroup_group_requires_non_empty_keys(
    group: types.ActionGroup, group_name: str
):
    with pytest.raises(ValueError):
        group.group(group_name)


@given(action_group(), text(whitespace, min_size=1))
def test_ActionGroup_group_requires_keys_without_whitespace(
    group: types.ActionGroup, group_name: str
):
    with pytest.raises(ValueError):
        group.group(group_name)


@given(action_group(), fragment())
def test_ActionGroup_group_requires_unique_keys(
    group: types.ActionGroup, group_name: str
):
    assume(group_name not in group.children)
    group.group(group_name)
    with pytest.raises(ValueError):
        group.group(group_name)


@given(action_group(), fragment())
def test_ActionGroup_action_creates_actions(group: types.ActionGroup, action_name: str):
    assume(action_name not in group.children)
    group.action(action_name)(utils.noop)
    assert action_name in group.children

    created_action = group.children[action_name]
    assert isinstance(created_action, types.Action)
    assert created_action.action == utils.noop


@given(action_group(), text(max_size=0))
def test_ActionGroup_action_requires_non_empty_keys(
    group: types.ActionGroup, action_name: str
):
    with pytest.raises(ValueError):
        group.action(action_name)


@given(action_group(), text(alphabet=whitespace))
def test_ActionGroup_action_requires_keys_without_whitespace(
    group: types.ActionGroup, action_name: str
):
    with pytest.raises(ValueError):
        group.action(action_name)


@given(action_group(), fragment())
def test_ActionGroup_action_requires_unique_keys(
    group: types.ActionGroup, action_name: str
):
    assume(action_name not in group.children)
    group.action(action_name)(utils.noop)

    with pytest.raises(ValueError):
        group.action(action_name)


@given(
    action_group(),
    fragment(),
    lists(action_param(), min_size=1),
    lists(action_param(), min_size=1),
)
def test_param_creates_params(
    group: types.ActionGroup,
    action_name: str,
    decorator_params: List[types.ActionParam],
    params: List[types.ActionParam],
):
    assume(action_name not in group.children)
    for param in params:
        types.param(param.source)(utils.noop)

    group.action(action_name, params=decorator_params)(utils.noop)

    created_action = group.children[action_name]
    if isinstance(created_action, types.ActionGroup):
        assert False, "Invalid state where action group is created from call to action"

    if created_action.params is None:
        assert False, "Invalid state where action is not supplied parameters"

    assert len(created_action.params) == len(decorator_params) + len(params)

    for created_param, sample_param in zip(
        created_action.params, decorator_params + list(reversed(params))
    ):
        assert created_param.source == sample_param.source


@given(action_group(), fragment(), action_param())
def test_param_warns_on_failure_to_apply_parameter_to_action(
    group: types.ActionGroup, action_name: str, param: types.ActionParam
):
    assume(action_name not in group.children)
    group.action(action_name)(utils.noop)

    # XXX: hypothesis's generation of an ActionGroup has it's own scoping which is why
    # the messy global _decorator_staging is marshalled elsewhere to this test's scope.
    # So we NEED to manually mark the sentinel. I know, this is disgusting
    types._decorator_staging[utils.noop] = None

    with pytest.warns(UserWarning):
        types.param(param.source)(utils.noop)

    created_action = group.children[action_name]
    if isinstance(created_action, types.ActionGroup):
        assert False, "Invalid state where action group is created from call to action"

    if created_action.params is None:
        assert False, "Invalid state where action is not supplied parameters"

    assert len(created_action.params) == 0
