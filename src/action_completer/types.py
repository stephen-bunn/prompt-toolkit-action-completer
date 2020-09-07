# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains the base data types used to power the completion and validation of actions.

Attributes:
    ActionCompletable_T (typing.Type): Defines the base data types that are typically
        used for completion. This type feels like it should be used more, but it really
        isn't necessary that often.

    ActionContext_T (typing.Type): Defines the value types to expect from the
        extraction of the context for the provided prompt document. Since we need
        various details about the current state of the prompt buffer, we explicitly
        define the types of the extracted context tuple through this type.

    ActionParamBasic_T (typing.Type): Defines the allowable types for basic completion
        and validation. Typically just a single value, in this case a string.

    ActionParamIterable_T (typing.Type): Defines the allowable types for iterable
        completion and validation. Only supports hashable iterables (tuples, lists) of
        strings.

    ActionParamCompleter_T (typing.Type): Defines the allowable types for nested
        completer completion (not validation). Currently just an alias of
        :class:`~prompt_toolkit.completion.Completer`.

    ActionParamCallable_T (typing.Type): Defines the allowable type for callable
        completions and validation.

    ActionParamSource_T (typing.Type): Defines the allowable types for action parameter
        sources that can be completed and validated. This is a union of previously
        defined action param types.

    ActionParamValidator_T (typing.Type): Defines the allowable types for validation
        callables or instances.

    LazyString_T (typing.Type): Defines the allowable types for optionally lazy
        evaluated strings. This is either just an instance of a string or a callable
        that results in a string.

    LazyText_T (typing.Type): Similar to :data:`~LazyString_T`, this defines the
        allowable types for optionally lazy evaluated strings or instances of
        :class:`~prompt_toolkit.formatted_text.FormattedText`. This is either just an
        instance or a callable that results in an instance.
"""

import re
import warnings
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

import attr
from prompt_toolkit.completion import Completer
from prompt_toolkit.filters import Filter
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.validation import Validator

_decorator_staging: Dict[object, Optional[List["ActionParam"]]] = {}

ActionCompletable_T = Union["ActionGroup", "Action", "ActionParam"]
ActionContext_T = Tuple[
    Optional["ActionGroup"], Optional[str], Union["ActionGroup", "Action"], List[str]
]
ActionParamBasic_T = str
ActionParamCallable_T = Callable[["Action", "ActionParam", str], Iterable[str]]
ActionParamCompleter_T = Type[Completer]
ActionParamIterable_T = Union[List[str], Tuple[str]]
ActionParamSource_T = Union[
    ActionParamBasic_T,
    ActionParamIterable_T,
    ActionParamCompleter_T,
    ActionParamCallable_T,
]
ActionParamValidator_T = Union[
    Validator, Callable[["ActionParam", str, List[str]], Any]
]
LazyString_T = Union[str, Callable[[ActionCompletable_T, str], str]]
LazyText_T = Union[
    str, FormattedText, Callable[[ActionCompletable_T, str], Union[str, FormattedText]]
]


@attr.s
class ActionParam:
    """Defines a completable action parameter.

    Attributes:
        source (:data:`~ActionParamSource_T`): The completion source for the parameter
        cast (Optional[~typing.Type], optional): The type to cast the action parameter
            to during execution of the action tied to this parameter
        style (Optional[:data:`~LazyString_T`], optional): The style string to apply to
            completion results for the action parameter
        selected_style (Optional[:data:`~LazyString_T`], optional): The style string to
            apply to selected completion results for the action parameter
        display (Optional[:data:`~LazyText_T`], optional): The custom display to apply
            to completion results for the action parameter
        display_meta (Optional[:data:`~LazyText_T`], optional): The custom display meta
            (description) to apply to completion results for the action parameter
        validators (Optional[List[:data:`~ActionParamValidator_T`]], optional): The
            list of validators to run in-order against the parameter value during
            validation
    """

    source: ActionParamSource_T = attr.ib()
    cast: Optional[Type] = attr.ib(default=None)
    style: Optional[LazyString_T] = attr.ib(default=None)
    selected_style: Optional[LazyString_T] = attr.ib(default=None)
    display: Optional[LazyText_T] = attr.ib(default=None)
    display_meta: Optional[LazyText_T] = attr.ib(default=None)
    validators: Optional[List[ActionParamValidator_T]] = attr.ib(default=None)


@attr.s
class Action:
    """Defines a completable action.

    Attributes:
        action (Optional[Callable[..., Any]], optional): The callable function that
            should be completeable and can be called after validation of the given
            action and associated parameters
        params (Optional[List[ActionParam]], optional): The list of action parameters
            in the same order of positional arguments for the ``action`` callable.
        style (Optional[:data:`~LazyString_T`], optional): The style string to apply to
            completion results for the action
        selected_style (Optional[:data:`~LazyString_T`], optional): The style string to
            apply to selected completion results for the action
        display (Optional[:data:`~LazyText_T`], optional): The custom display to apply
            to completion results for the action
        display_meta (Optional[:data:`~LazyText_T`], optional): The custom display meta
            (description) to apply to completion results for the action
        active (Optional[~prompt_toolkit.filters.Filter], optional): A callable filter
            that results in a boolean to indicate if the action should be considred as
            active and displayed as a completion result
        capture_all (bool, optional): If there is the option for this action to accept
            more arguments than defined by the provided parameters, this flag will
            allow for any number of following arguments (after parameters) as additional
            positional arguments to the provided ``action`` callable, defaults to False
    """

    action: Optional[Callable[..., Any]] = attr.ib(default=None)
    params: Optional[List[ActionParam]] = attr.ib(default=None)
    style: Optional[LazyString_T] = attr.ib(default=None)
    selected_style: Optional[LazyString_T] = attr.ib(default=None)
    display: Optional[LazyText_T] = attr.ib(default=None)
    display_meta: Optional[LazyText_T] = attr.ib(default=None)
    active: Optional[Filter] = attr.ib(default=None)
    capture_all: bool = attr.ib(default=False)


@attr.s
class ActionGroup:
    """Defines a completable group of either nested action groups or leaf actions.

    .. important::
        It is crucial for proper fragment extraction that no children keys contain
        spaces. Each non-escaped space is considered a new fragment and used to
        find the context for both completion and validation. Although it would
        technically be possible to support child key completion with spaces, it involves
        more complex features of prompt-toolkit than *just* completion.

        Therefore, I have decided to hold the opinion that no spaces should be
        allowable as keys in a group's children. A post-initialization validator exists
        to ensure this is true for any action group you define.

    Attributes:
        children (Dict[str, Union[ActionGroup, Action]]): The dictionary of completion
            text (keys) to a nested action group or a callable action (value) that forms
            the group's children
        style (Optional[:data:`~LazyString_T`], optional): The style string to apply to
            completion results for the action group
        selected_style (Optional[:data:`~LazyString_T`], optional): The style string to
            apply to selected completion results for the action group
        display (Optional[:data:`~LazyText_T`], optional): The custom display to apply
            to completion results for the action group
        display_meta (Optional[:data:`~LazyText_T`], optional): The custom display meta
            (description) to apply to completion results for the action group
        active (Optional[~prompt_toolkit.filters.Filter], optional): A callable filter
            that results in a boolean to indicate if the action group should be
            considred as active and displayed as a completion result
    """

    children: Dict[str, Union["ActionGroup", Action]] = attr.ib()
    style: Optional[LazyString_T] = attr.ib(default=None)
    selected_style: Optional[LazyString_T] = attr.ib(default=None)
    display: Optional[LazyText_T] = attr.ib(default=None)
    display_meta: Optional[LazyText_T] = attr.ib(default=None)
    active: Optional[Filter] = attr.ib(default=None)

    @children.validator
    def _children_validator(self, attribute: attr.Attribute, value: dict):
        """Validate the children attribute for the group on instance creation.

        Args:
            attribute (attr.Attribute): The attribute to validate
            value (dict): The value of the children attribute

        Raises:
            ValueError: When any children keys contain no characters or contain spaces
        """

        invalid_names = [
            name for name in value if len(name) <= 0 or re.findall(r"\s+", name)
        ]
        if invalid_names:
            raise ValueError(
                "group children can not use names without characters or names "
                f"including spaces, {invalid_names!r}"
            )

    def group(
        self,
        name: str,
        children: Optional[Dict[str, Union["ActionGroup", Action]]] = None,
        style: Optional[LazyString_T] = None,
        selected_style: Optional[LazyString_T] = None,
        display: Optional[LazyText_T] = None,
        display_meta: Optional[LazyText_T] = None,
        active: Optional[Filter] = None,
    ) -> "ActionGroup":
        """Create a new subgroup for the current group.

        By default the :class:`~action_completer.completer.ActionCompleter` comes with
        a ``root`` group to extend from. However, if you want to build a set of nested
        commands, you can use this function to register a new group on the completer.

        .. code-block:: python

            from prompt_toolkit.shortcuts import prompt
            from action_completer import ActionCompleter
            completer = ActionCompleter()

            nested_group = completer.group("hello")

            @nested_group.action("world")
            def _hello_world_action():
                print("Hello, World!")


            completer.run_action(prompt(">>> ", completer=completer))
            # available through the following prompt:
            # >>> hello world
            # Hello, World!

        Args:
            name (str): The completion text that triggers this group
            children (Dict[str, Union[ActionGroup, Action]]): The dictionary of
                completion text (keys) to a nested action group or a callable action
                (value) that forms the group's children
            style (Optional[:data:`~LazyString_T`], optional): The style string to
                apply to completion results for the action group
            selected_style (Optional[:data:`~LazyString_T`], optional): The style string
                to apply to selected completion results for the action group
            display (Optional[:data:`~LazyText_T`], optional): The custom display to
                apply to completion results for the action group
            display_meta (Optional[:data:`~LazyText_T`], optional): The custom display
                meta (description) to apply to completion results for the action group
            active (Optional[~prompt_toolkit.filters.Filter], optional): A callable
                filter that results in a boolean to indicate if the action group should
                be considred as active and displayed as a completion result

        Raises:
            ValueError: When the provided group name contains spaces
            ValueError: When the provided group name is already in the current group

        Returns:
            ActionGroup: The created action group
        """

        if len(name) <= 0:
            raise ValueError(f"group names must contain characters, {name!r}")
        if re.findall(r"\s+", name):
            raise ValueError(f"groups can not use names including whitespace, {name!r}")
        if name in self.children:
            raise ValueError(
                f"name {name!r} already registered as {self.children[name]!r}"
            )

        group = ActionGroup(
            children=children or {},
            style=style,
            selected_style=selected_style,
            display=display,
            display_meta=display_meta,
            active=active,
        )

        self.children[name] = group
        return group

    def action(
        self,
        name: str,
        params: Optional[List[ActionParam]] = None,
        style: Optional[LazyString_T] = None,
        selected_style: Optional[LazyString_T] = None,
        display: Optional[LazyText_T] = None,
        display_meta: Optional[LazyText_T] = None,
        active: Optional[Filter] = None,
        capture_all: bool = False,
    ) -> Callable[..., Any]:
        """Decorate a callable as an action within the current group.

        Basic root level actions are easily defined directly off of the completer
        instance like follows:

        .. code-block:: python

            from prompt_toolkit.shortcuts import prompt
            from action_completer import ActionCompleter
            completer = ActionCompleter()

            @completer.action("hello")
            def _hello_action():
                print("Hello, World!")

            completer.run_action(prompt(">>> ", completer=completer))

            # available through the following prompt:
            # >>> hello
            # Hello, World!

        You can nest actions in sub-groups by first calling
        :meth:`~ActionGroup.group` to define a new group and base all actions
        from the ``action`` decorator provided on that new group.

        Args:
            name (str): The completion name that triggers this action
            params (Optional[List[ActionParam]], optional): The list of action
                parameters to complete and handle within the action
            style (Optional[:data:`~LazyString_T`], optional): The style string to apply
                to completion results for the action
            selected_style (Optional[:data:`~LazyString_T`], optional): The style string
                to apply to selected completion results for the action
            display (Optional[:data:`~LazyText_T`], optional): The custom display to
                apply to completion results for the action
            display_meta (Optional[:data:`~LazyText_T`], optional): The custom display
                meta (description) to apply to completion results for the action
            active (Optional[~prompt_toolkit.filters.Filter], optional): A callable
                filter that results in a boolean to indicate if the action group should
                be considred as active and displayed as a completion result
            capture_all (bool, optional): If there is the option for this action to
                accept more arguments than defined by the provided parameters, this flag
                will allow for any number of following arguments (after parameters) as
                additional positional arguments to the provided ``action`` callable,
                defaults to False

        Raises:
            ValueError: When the given action name contains spaces
            ValueError: When the given action name is already present in the group

        Returns:
            Callable[..., Any]: The newly wrapped action callable
        """

        if len(name) <= 0:
            raise ValueError(f"action names must contain characters, {name!r}")
        if re.findall(r"\s+", name):
            raise ValueError(
                f"actions can not use names including whitespace, {name!r}"
            )
        if name in self.children:
            raise ValueError(
                f"name {name!r} already registered as {self.children[name]!r}"
            )

        def action_wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
            action_parameters = []
            if params:
                action_parameters.extend(params)

            action_parameters.extend(reversed(_decorator_staging.get(func) or []))

            action = Action(
                action=func,
                params=action_parameters,
                style=style,
                selected_style=selected_style,
                display=display,
                display_meta=display_meta,
                active=active,
                capture_all=capture_all,
            )

            # Delete the staged action parameters for a specific function if available
            if func in _decorator_staging:
                del _decorator_staging[func]
            else:
                # In case we don't detect any available parameters we are marking the
                # function as None indicating that no parameters were dynamically added
                # to the action with the staging dictionary.

                # This is later used in the @param decorator to determine if a parameter
                # is being added to an already registered action and therefore the param
                # SHOULD NOT (not could not) be added to the action. This None value is
                # used as a sentinel to indicate the action has already been registered.
                # Any state where action is not currently registered should be either:
                #     1. The function does not appear in the dictionary
                #     2. The dictionary value for the function key is an instance of a
                #        list of ActionParams
                _decorator_staging[func] = None

            self.children[name] = action
            return func

        return action_wrapper


def param(
    source: ActionParamSource_T,
    cast: Optional[Type] = None,
    style: Optional[LazyString_T] = None,
    selected_style: Optional[LazyString_T] = None,
    display: Optional[LazyText_T] = None,
    display_meta: Optional[LazyText_T] = None,
    validators: Optional[List[ActionParamValidator_T]] = None,
) -> Callable[..., Any]:
    """Create a new action parameter for an action.

    Basic parameters can be defined right before defining a method as an action.

    .. code-block::

        from pathlib import Path
        from prompt_toolkit.shortcuts import prompt
        from prompt_toolkit.validation import Validator
        from action_completer import ActionCompleter
        completer = ActionCompleter()

        @completer.action("cat")
        @completer.param(
            PathCompleter(),
            cast=Path,
            validators=[Validator.from_callable(lambda p: Path(p).is_file())]
        )
        def _cat_action(filepath: Path):
            with filepath.open("r") as file_handle:
                print(file_handle.read())

        completer.run_action(prompt(">>> ", completer=completer))
        # available through the following prompt:
        # # $ echo "my content" > ./my-file.txt
        # >>> cat ./my-file.txt
        # my content


    .. important::
        The application order of ``param`` decorators is very important. Since these
        defined action parameters are applied as positional arguments to the action, we
        are opinionated on the ordering that decorators should be applied.

        We purposefully reverse the traditional decorator application order to make the
        readability of actions created purely through decorators a bit easier. This
        means that the **last** parameter should be the **first** decorator applied to
        the action callable, and the **very last** decorator applied to the action
        callable should be the action decorator. This benefits readability by ordering
        the defined param decorators top-to-bottom as arguments applied left-to-right
        in the action callable.

        .. code-block:: python

            # valid
            @action("test")
            @param("source1")
            @param("source2")
            def _valid_action(source1: str, source2: str):
                ...

            # invalid
            @param("source2")
            @param("source1")
            @action("test")
            def _invalid_action(source1: str, source2: str):
                ...

            # also invalid
            @action("test")
            @param("source2")
            @param("source1")
            def _also_invalid_action(source1: str, source2: str):
                ...


        We have *some* checks to raise warnings in case you accidentally use an invalid
        spec for applying the decorators. Although I'm not 100% sure it will capture
        all the possible states of defining actions that you might come up with.

        If you don't like this design, I would recommend you instead pass
        :class:`~ActionParam` instances to the ``params`` keyword argument when
        using the :meth:`~ActionGroup.action` decorator.

    Args:
        source (:data:`~ActionParamSource_T`): The completion source for the parameter
        cast (Optional[~typing.Type], optional): The type to cast the action parameter
            to during execution of the action tied to this parameter
        style (Optional[:data:`~LazyString_T`], optional): The style string to apply to
            completion results for the action parameter
        selected_style (Optional[:data:`~LazyString_T`], optional): The style string to
            apply to selected completion results for the action parameter
        display (Optional[:data:`~LazyText_T`], optional): The custom display to apply
            to completion results for the action parameter
        display_meta (Optional[:data:`~LazyText_T`], optional): The custom display meta
            (description) to apply to completion results for the action parameter
        validators (Optional[List[:data:`~ActionParamValidator_T`]], optional): The
            list of validators to run in-order against the parameter value during
            validation

    Returns:
        Callable[..., Any]: The newly wrapped action with the defined parameters
    """

    def param_wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        action_param = ActionParam(
            source=source,
            cast=cast,
            style=style,
            selected_style=selected_style,
            display=display,
            display_meta=display_meta,
            validators=validators,
        )

        parameter_store = _decorator_staging.get(func, [])
        # When the parameter's function is already registered and marked with the None
        # sentinel, we are attempting to add a parameter to an action that has already
        # been registered and therefore should not have any more parameters added.
        if parameter_store is None:
            warnings.warn(
                f"Action parameter with source {source!r} for {func!r} could not be "
                "applied to the already registered action, make sure you decorate the "
                "action callable with the @action decorator last "
                "(on top of all @param decorators)",
                UserWarning,
            )
            return func

        parameter_store.append(action_param)
        _decorator_staging[func] = parameter_store
        return func

    return param_wrapper
