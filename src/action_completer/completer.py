# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains the completer for a single root :class:`~.types.ActionGroup` instance.

Registering actions for the completer can be done in several different ways.
The simplest way, is to use the provided :meth:`~.types.ActionGroup.action` decorator:

.. code-block:: python

    from prompt_toolkit.shortcuts import prompt
    from action_completer import ActionCompleter
    completer = ActionCompleter()

    @completer.action("hello")
    def _hello_world():
        print("Hello, World!")

    completer.run_action(prompt(">>> ", completer=completer))


Another common way is to build the root :class:`~.types.ActionGroup` structure yourself:

.. code-block:: python

    from prompt_toolkit.shortcuts import prompt
    from action_completer import ActionCompleter, ActionGroup, Action

    def _hello_world():
        print("Hello, World!")

    root_group = ActionGroup({"hello": Action(_hello_world)})
    completer = ActionCompleter(root_group)

    completer.run_action(prompt(">>> ", completer=completer))


Lastly, if you *really* need it, you can specify the starting structure of the completer
through a **very specific** dictionary structure. I personally needed this in the past
and haven't yet had the chance to remove the need of it.

.. code-block:: python

    from prompt_toolkit.shortcuts import prompt
    from action_completer import ActionCompleter

    def _hello_world():
        print("Hello, World!")

    completer = ActionCompleter.from_dict({
        "root": {
            "hello": {
                "action": _hello_world
            }
        },
        "fuzzy_tolerance: 75
    })

    completer.run_action(prompt(">>> ", completer=completer))
"""

import warnings
from functools import partial
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Generator,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

import attr
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.validation import ValidationError, Validator
from typing_extensions import Protocol

from .types import (
    Action,
    ActionCompletable_T,
    ActionGroup,
    ActionParam,
    LazyText_T,
    param,
)
from .utils import (
    decode_completion,
    encode_completion,
    extract_context,
    get_dynamic_value,
    get_fragments,
    iter_best_choices,
    noop,
)
from .validator import ActionValidator

DEFAULT_FUZZY_TOLERANCE = 75


class CompletionIterator_T(Protocol):
    """Protocol typing for top-level (non-param) Completion generators.

    Required for dynamic switching between group and action completion iterators since
    both ActionGroup and Action can appear as values in ActionGroup.children.
    """

    def __call__(  # noqa: D102
        self,
        source: Union[ActionGroup, Action],
        fragments: List[str],
        complete_event: CompleteEvent,
        start_position: int = 0,
    ) -> Generator[Completion, None, None]:
        ...  # pragma: no cover


class ActionParamCompletionIterator_T(Protocol):
    """Protocol typing for param-level Completion generators.

    Required for dynamic switching between various action param completion interators.
    """

    def __call__(  # noqa: D102
        self,
        action: Action,
        action_param: ActionParam,
        param_value: str,
        complete_event: CompleteEvent,
        start_position: int = 0,
    ) -> Generator[Completion, None, None]:
        ...  # pragma: no cover


@attr.s
class ActionCompleter(Completer):
    """Custom completer for actions.

    This completer should be relatively easy to consume and provides features for
    extending completions with custom styles and display properties.

    The most straight forward method of defining actions is to use the
    :meth:`~.types.ActionGroup.action` decorator right off of the completer:

    .. code-block:: python

        from prompt_toolkit.shortcuts import prompt
        from action_completer import ActionCompleter
        completer = ActionCompleter()

        @completer.action("hello")
        def _hello_world():
            print("Hello, World!")

        output = prompt(">>> ", completer=completer)
        completer.run_action(output)

        # >>> hello
        # Hello, World!


    If you want to go a more declarative route, you can explicitly build the tree
    structure of :class:`~.types.ActionGroup`, :class:`~.types.Action`, and
    :class:`~.types.ActionParam` yourself.

    .. code-block:: python

        from prompt_toolkit.shortcuts import prompt
        from action_completer import ActionCompelter, ActionGroup, Action, ActionParam

        def _hello_world():
            print("Hello, World!")

        ACTIONS = ActionGroup({
            "hello": Action(_hello_world)
        })

        completer = ActionCompleter(ACTIONS)

        output = prompt(">>> ", completer=completer)
        completer.run_action(output)

        # >>> hello
        # Hello, World!
    """

    root: ActionGroup = attr.ib(default=None)
    fuzzy_tolerance: int = attr.ib(default=DEFAULT_FUZZY_TOLERANCE)

    def __attrs_post_init__(self):
        """Class post-initialization handler."""

        if not self.root:
            self.root = ActionGroup(children={})

        if any(
            (
                self.root.style,
                self.root.selected_style,
                self.root.display,
                self.root.display_meta,
            )
        ):
            warnings.warn(
                "Display parameters (display, display_meta, style, selected_style) are "
                "never presented on the root action group, please remove any of these "
                "parameters from the root action group",
                UserWarning,
            )

        # alias completer.group and completer.action to the root action group's methods
        self.group = self.root.group
        self.action = self.root.action
        self.param = param

    def _compare_string(self, partial_string: str, full_string: str) -> bool:
        """Check if a source string is contained within a target string.

        Args:
            partial_string (str): The string that should be contained within the target
            full_string (str): The string that should contain the source

        Returns:
            bool: True if the source is contained by the target, otherwise False
        """

        # It may seem weird to put a simple `in` check in its own method. I've run
        # into refactor hell many times in the past from developers not isolating
        # responsibility such as this correctly.

        return partial_string in full_string

    def _get_completion_style(
        self,
        completable: ActionCompletable_T,
        text: str,
        override: Optional[str] = None,
    ) -> str:
        """Get the appropriate completion style for a given source.

        Args:
            completable (ActionCompletable_T): The completable source instance to
                extract the appropriate style from
            text (str): The text used to trigger the current source
            override (Optional[str], optional): An explicit override for any style
                (typically used from nested completers)

        Returns:
            str: The appropriate style string, may be blank when desired
        """

        if override:
            return override

        if completable.style:
            dynamic_style = get_dynamic_value(completable, completable.style, text)
            if isinstance(dynamic_style, str):
                return dynamic_style

        return ""

    def _get_completion_selected_style(
        self,
        completable: ActionCompletable_T,
        text: str,
        override: Optional[str] = None,
    ) -> str:
        """Get the appropriate completion selected style for a given source.

        Args:
            completable (ActionCompletable_T): The completable source instance to
                extract the appropriate style from
            text (str): The text used to trigger the current source
            override (Optional[str], optional): An explicit override for any selected
                style (typically used from nested completers)

        Returns:
            str: The appropriate selected style string, may be blank when desired
        """

        if override:
            return override

        if completable.selected_style:
            dynamic_selected_style = get_dynamic_value(
                completable, completable.selected_style, text
            )
            if isinstance(dynamic_selected_style, str):
                return dynamic_selected_style

        return ""

    def _get_completion_display(
        self,
        completable: ActionCompletable_T,
        text: str,
        override: Optional[LazyText_T] = None,
    ) -> Optional[Union[str, FormattedText]]:
        """Get the appropriate completion display for a given source.

        Args:
            completable (ActionCompletable_T): The completable source instance to
                extract the appropriate completion display from
            text (str): The text used to trigger the current source
            override (Optional[LazyText_T], optional): An explicit override for any
                display (typically used for nested completers)

        Returns:
            Optional[Union[str, FormattedText]]: The appropriate display value, may be
                None when desired
        """

        if override:
            return get_dynamic_value(completable, override, text)

        if completable.display:
            return get_dynamic_value(completable, completable.display, text)

        return None

    def _get_completion_display_meta(
        self,
        completable: ActionCompletable_T,
        text: str,
        override: Optional[LazyText_T] = None,
    ) -> Union[str, FormattedText]:
        """Get the appropriate completion display_meta (description) for a given source.

        Args:
            completable (ActionCompletable_T): The completable source instance to
                extract the appropriate completion display_meta from
            text (str): The text used to trigger the current source
            override (Optional[LazyText_T], optional): An explicit override for any
                display_meta (typically used for nested completers)

        Returns:
            Union[str, FormattedText]: The appropriate display_meta value, may be None
                when desired
        """

        if override:
            dynamic_display_meta = get_dynamic_value(completable, override, text)
            if dynamic_display_meta:
                return dynamic_display_meta
        elif completable.display_meta:
            dynamic_display_meta = get_dynamic_value(
                completable, completable.display_meta, text
            )
            if dynamic_display_meta:
                return dynamic_display_meta

        return ""

    def _build_completion(
        self,
        completable: ActionCompletable_T,
        text: str,
        start_position: int = 0,
        style: Optional[str] = None,
        selected_style: Optional[str] = None,
        display: Optional[LazyText_T] = None,
        display_meta: Optional[LazyText_T] = None,
    ) -> Completion:
        """Build the completion that should be yielded by a completion generator.

        Args:
            completable (ActionCompletable_T): The completable source instance to
                extract the appropriate display description from
            text (str): The text used to trigger the completion
            start_position (int, optional): The starting position of the completion.
                Defaults to 0.
            style (Optional[str], optional): Style override to use for the completion
            selected_style (Optional[str], optional): Selected style override to use for
                the completion
            display (Optional[LazyText_T], optional): Display override to use for the
                completion
            display_meta (Optional[LazyText_T], optional): Display meta (description)
                override to use for the completion

        Returns:
            Completion: A completion instance for the given source and text
        """

        return Completion(
            text=text,
            start_position=start_position,
            style=self._get_completion_style(completable, text, style),
            selected_style=self._get_completion_selected_style(
                completable, text, selected_style
            ),
            display=self._get_completion_display(completable, text, display),
            display_meta=self._get_completion_display_meta(
                completable, text, display_meta
            ),
        )

    def _iter_group_completions(
        self,
        action_group: ActionGroup,
        fragments: List[str],
        complete_event: CompleteEvent,
        start_position: int = 0,
    ) -> Generator[Completion, None, None]:
        """Iterate completions for a given :class:`~types.ActionGroup`.

        Args:
            action_group (ActionGroup): The action group to generate completions for
            fragments (List[str]): The current list of extracted prompt fragments
            complete_event (CompleteEvent): The completion event for the completion
            start_position (int, optional): The starting position for the generated
                completions, defaults to 0

        Yields:
            Completion: A completion for the given action group with respect to the
                given prompt fragments
        """

        for completion_text in iter_best_choices(
            action_group.children.keys(),
            fragments[-1],
            fuzzy_tolerance=self.fuzzy_tolerance,
        ):
            source = action_group.children[completion_text]
            if source.active is not None and not source.active():
                continue

            yield self._build_completion(
                completable=source,
                text=completion_text,
                start_position=start_position,
            )

    def _iter_basic_param_completions(
        self,
        action: Action,
        action_param: ActionParam,
        param_value: str,
        complete_event: CompleteEvent,
        start_position: int = 0,
    ) -> Generator[Completion, None, None]:
        """Iterate basic (string) action parameter completions.

        Args:
            action (Action): The action the parameter is tied to
            action_param (ActionParam): The action parameter to generate completions for
            param_value (str): The current value of the parameter
            complete_event (CompleteEvent): The completion event for the completion
            start_position (int, optional): The starting position for the generated
                completions, defaults to 0

        Yields:
            Completion: A completion for the given basic action parameter with respect
                to the given parameter value
        """

        assert isinstance(
            action_param.source, str
        ), f"basic param completions can only handle a string source, {action_param!r}"

        if self._compare_string(param_value, action_param.source):
            yield self._build_completion(
                completable=action_param,
                text=action_param.source,
                start_position=start_position,
            )

    def _iter_iterable_param_completions(
        self,
        action: Action,
        action_param: ActionParam,
        param_value: str,
        complete_event: CompleteEvent,
        start_position: int = 0,
    ) -> Generator[Completion, None, None]:
        """Iterate iterable (Iterable[str]) action parameter completions.

        Args:
            action (Action): The action the parameter is tied to
            action_param (ActionParam): The action parameter to generate completions for
            param_value (str): The current value of the parameter
            complete_event (CompleteEvent): The completion event for the completion
            start_position (int, optional): The starting position for the generated
                completions, defaults to 0

        Yields:
            Completion: A completion for the given iterable action parameter with
                respect to the given parameter value
        """

        assert isinstance(action_param.source, (list, tuple,)), (
            "iterable param completions can only handle iterables of strings, "
            f"{action_param.source!r}"
        )

        for completion_text in iter_best_choices(
            action_param.source, param_value, fuzzy_tolerance=self.fuzzy_tolerance
        ):
            yield self._build_completion(
                completable=action_param,
                text=completion_text,
                start_position=start_position,
            )

    def _iter_completer_param_completions(
        self,
        action: Action,
        action_param: ActionParam,
        param_value: str,
        complete_event: CompleteEvent,
        start_position: int = 0,
    ) -> Generator[Completion, None, None]:
        """Iterate completer (Completer) action parameter completions.

        Args:
            action (Action): The action the parameter is tied to
            action_param (ActionParam): The action parameter to generate completions for
            param_value (str): The current value of the parameter
            complete_event (CompleteEvent): The completion event for the completion
            start_position (int, optional): The starting position for the generated
                completions, defaults to 0

        Yields:
            Completion: A completion for the given completer action parameter with
                respect to the given parameter value
        """

        assert isinstance(action_param.source, Completer), (
            "completer param completions can only handle instances of Completer, "
            f"{action_param.source!r}"
        )

        for completion in action_param.source.get_completions(
            Document(text=param_value), complete_event
        ):
            yield self._build_completion(
                completable=action_param,
                text=completion.text,
                start_position=completion.start_position,
                style=completion.style or None,
                display=completion.display or None,
                display_meta=(
                    completion._display_meta
                    if isinstance(completion._display_meta, (str, FormattedText))
                    else None
                ),
            )

    def _iter_callable_param_completions(
        self,
        action: Action,
        action_param: ActionParam,
        param_value: str,
        complete_event: CompleteEvent,
        start_position: int = 0,
    ) -> Generator[Completion, None, None]:
        """Iterate callable action parameter completions.

        Args:
            action (Action): The action the parameter is tied to
            action_param (ActionParam): The action parameter to generate completions for
            param_value (str): The current value of the parameter
            complete_event (CompleteEvent): The completion event for the completion
            start_position (int, optional): The starting position for the generated
                completions, defaults to 0

        Yields:
            Completion: A completion for the given callable action parameter with
                respect to the given parameter value
        """

        assert callable(action_param.source), (
            "callable param completions can only handle callables that return "
            f"iterables of strings, {action_param.source!r}"
        )

        completion_choices: Iterable[str] = action_param.source(  # type: ignore
            action, action_param, param_value
        )
        for completion_text in iter_best_choices(
            completion_choices,
            param_value,
            fuzzy_tolerance=self.fuzzy_tolerance,
        ):
            yield self._build_completion(
                completable=action_param,
                text=completion_text,
                start_position=start_position,
            )

    def _iter_none_param_completions(
        self,
        action: Action,
        action_param: ActionParam,
        param_value: str,
        complete_event: CompleteEvent,
        start_position: int = 0,
    ) -> Generator[Completion, None, None]:
        """Iterate None action parameter completions.

        .. important::
            None completions are not shown **unless** either a ``display`` or
            ``display_meta`` value is given. Without one of these value's being
            there is no point in rendering a completion as we can't predict what that
            completion might be.

        Args:
            action (Action): The action the parameter is tied to
            action_param (ActionParam): The action parameter to generate completions for
            param_value (str): The current value of the parameter
            complete_event (CompleteEvent): The completion event for the completion
            start_position (int, optional): The starting position for the generated
                completions, defaults to 0

        Yields:
            Completion: A completion for the given Non action parameter with respect to
                the given parameter value
        """

        assert action_param.source is None, (
            "none param completions will only handle parameters of source None, "
            f"{action_param.source!r}"
        )

        if action_param.display or action_param.display_meta:
            yield self._build_completion(
                completable=action_param,
                text=decode_completion(param_value),
                start_position=start_position,
            )

    def _iter_action_completions(
        self,
        action: Action,
        fragments: List[str],
        complete_event: CompleteEvent,
        start_position: int = 0,
    ) -> Generator[Completion, None, None]:
        """Iterate completions for a given :class:`~type.Action`.

        Args:
            action (Action): The action to generate completions for
            fragments (List[str]): The current list of extracted prompt fragments
            complete_event (CompleteEvent): The completion event for the completion
            start_position (int, optional): The starting position for the generated
                completions, defaults to 0

        Yields:
            Completion: A completion for the given action group with respect to the
                given prompt fragments
        """

        if action.params is None:
            return

        param_offset = len(fragments) - 1
        for action_param, param_value in zip(
            action.params[param_offset:], fragments[param_offset:]
        ):
            completion_iterator: Optional[ActionParamCompletionIterator_T] = None
            if isinstance(action_param.source, str):
                completion_iterator = self._iter_basic_param_completions
            elif isinstance(
                action_param.source,
                (
                    list,
                    tuple,
                ),
            ):
                completion_iterator = self._iter_iterable_param_completions
            elif isinstance(action_param.source, Completer):
                completion_iterator = self._iter_completer_param_completions
            elif callable(action_param.source):
                completion_iterator = self._iter_callable_param_completions
            elif action_param.source is None:
                completion_iterator = self._iter_none_param_completions

            if completion_iterator is not None:
                yield from completion_iterator(
                    action,
                    action_param,
                    param_value,
                    complete_event,
                    start_position,
                )

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Generator[Completion, None, None]:
        """Generate completions for the given prompt document.

        Args:
            document (~prompt_toolkit.document.Document): The document directly from
                the prompt to generate completions for
            complete_event (~prompt_toolkit.completion.CompleteEvent): The completion
                event for the completions

        Yields:
            prompt_toolkit.completion.Completion:
                A completion for the given prompt document
        """

        _, _, completable, fragments = extract_context(
            self.root, get_fragments(document.text)
        )

        if len(fragments) <= 0:
            return

        # this starting position is NOT the same as len(document.text)
        start_position = -len(" ".join(fragments))
        completion_iterator: Optional[CompletionIterator_T] = None
        if isinstance(completable, ActionGroup):
            completion_iterator = cast(
                CompletionIterator_T, self._iter_group_completions
            )
        elif isinstance(completable, Action):
            completion_iterator = cast(
                CompletionIterator_T, self._iter_action_completions
            )

        if completion_iterator:
            for completion in completion_iterator(
                completable, fragments, complete_event, start_position=start_position
            ):
                completion.text = encode_completion(completion.text)
                yield completion

    def get_validator(self) -> ActionValidator:
        """Get an instance of the validator for the current completer.

        Returns:
            ActionValidator: A prompt validator for the current state of the completer
        """

        return ActionValidator(root=self.root)

    def _iter_partial_action_parameters(
        self, action: Action, fragments: List[str]
    ) -> Generator[Any, None, None]:
        """Iterate clean action callable parameters for the given prompt fragments.

        Args:
            action (Action): The action being executed
            fragments (List[str]): The list of current prompt buffer fragments

        Yields:
            Any: Parameter values for the given action's parameters
        """

        if not action.params or len(action.params) <= 0 or len(fragments) <= 0:
            return

        for action_param, param_value in zip(
            action.params, list(map(decode_completion, fragments))
        ):
            if not action_param.cast:
                yield param_value
                continue

            yield action_param.cast(param_value)

        if action.capture_all:
            yield from fragments[len(action.params) :]

    def get_partial_action(self, prompt_result: str) -> Callable[..., Any]:
        """Get the partial for the action callable with action parameters included.

        Args:
            prompt_result (str): The result of the completer's prompt call

        Raises:
            ValueError: When no actionable action can be determined from the given
                prompt result

        Returns:
            Callable[..., Any]:
                A partial callable for the related action including clean parameters
        """

        prompt_result = prompt_result.strip()
        _, _, relative_action, fragments = extract_context(
            self.root, get_fragments(prompt_result)
        )
        if not isinstance(relative_action, Action):
            raise ValueError(
                f"no action discovered for {prompt_result!r}, "
                f"resolved relative {relative_action!r}"
            )

        return (
            partial(
                relative_action.action,
                *self._iter_partial_action_parameters(relative_action, fragments),
            )
            if relative_action.action is not None
            else partial(noop)
        )

    def run_action(self, prompt_result: str, *args, **kwargs) -> Any:
        """Run the related action from the given prompt result.

        Args:
            prompt_result (str): The result of the completer's prompt call

        Returns:
            Any: Whatever the return value of the related action callable is
        """

        return self.get_partial_action(prompt_result)(*args, **kwargs)
