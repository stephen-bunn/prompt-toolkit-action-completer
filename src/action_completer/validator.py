# -*- encoding: utf-8 -*-
# Copyright (c) 2020 Stephen Bunn <stephen@bunn.io>
# ISC License <https://choosealicense.com/licenses/isc>

"""Contains the validator used to validate data produced by the action completer.

To retreive this validator, it is highly recommend that you utilize the
:meth:`~.completer.ActionCompleter.get_validator` method.
If your completer instance is dynamic, you probably want to fetch this validator
instance for every call to :func:`~prompt_toolkit.shortcuts.prompt`.

For example:

.. code-block:: python

    from prompt_toolkit.shortcuts import prompt
    from action_completer import ActionCompleter
    completer = ActionCompleter()

    # ... register completer actions

    while True:
        # note the call to `get_validator` for every call to prompt
        prompt_result = prompt(
            ">>> ",
            completer=completer,
            validator=completer.get_validator()
        )


You could also initialize the :class:`~ActionValidator` yourself by passing
through the ``root`` group of the :class:`~.completer.ActionCompleter`:

.. code-block:: python

    from prompt_toolkit.shortcuts import prompt
    from action_completer import ActionCompleter, ActionValidator
    completer = ActionCompleter()

    # ... register completer actions

    while True:
        validator = ActionValidator(completer.root)
        prompt_result = prompt(
            ">>> ",
            completer=completer,
            validator=validator
        )
"""

import operator
import warnings
from typing import Iterable, List, Optional, Tuple, Union

import attr
from fuzzywuzzy import process as fuzzy_process
from fuzzywuzzy import utils as fuzzy_utils
from prompt_toolkit.completion import Completer
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError, Validator

from .types import Action, ActionGroup, ActionParam
from .utils import decode_completion, extract_context, get_best_choice, get_fragments


@attr.s
class ActionValidator(Validator):
    """Custom validator for a :class:`~.completer.ActionCompleter`.

    Most of the time you should get this instance from
    :meth:`~.completer.ActionCompleter.get_validator` however if you need to build an
    instance of it yourself you can use the following logic:

    .. code-block:: python

        from action_completer.completer import ActionCompleter
        from action_completer.validator import ActionValidator

        completer = ActionCompleter()
        validator = ActionValidator(completer.root)
    """

    root: ActionGroup = attr.ib()

    def _validate_choices(
        self, choices: Union[List[str], Tuple[str]], text: str, cursor_position: int = 0
    ):
        """Validate the given text falls within the given choices.

        Args:
            choices (Union[List[str], Tuple[str]]): The choices to validate against
            text (str): The text to validate against the given choices
            cursor_position (int, optional): The current cursor position in the prompt
                buffer. Defaults to 0.

        Raises:
            ValidationError: When the given text does not match the supplied choice,
                if a single choice is given
            ValidationError: When the given text does not fall within the given choices,
                if multiple choices are provided
        """

        if len(choices) <= 0 or len(text) <= 0:
            return

        if len(choices) == 1 and text != choices[0]:
            raise ValidationError(
                message=f"Invalid value {text!r}, expected {choices[0]!r}",
                cursor_position=cursor_position,
            )

        if text not in choices:
            message = f"Invalid value {text!r}"
            best_guess = get_best_choice(choices, text)
            if best_guess:
                message += f", did you mean {best_guess!r}"

            raise ValidationError(message=message, cursor_position=cursor_position)

    def _validate_group(
        self,
        action_group: ActionGroup,
        fragments: List[str],
        parent_name: Optional[str] = None,
        cursor_position: int = 0,
    ):
        """Validate the prompt buffer fragments are valid against an action group.

        Args:
            action_group (ActionGroup): The action group to base validation off of
            fragments (List[str]): The current prompt buffer fragments to validate
            parent_name (Optional[str], optional): The name of the parent task that
                triggered the current action group. Defaults to None.
            cursor_position (int, optional): The current cursor position in the prompt
                buffer. Defaults to 0.

        Raises:
            ValidationError: When the given text fragments are not valid against the
                provided action group
        """

        available_choices = [
            name
            for name, child in action_group.children.items()
            if child.active is None or child.active()
        ]

        # XXX: I'm a little confused about when this state is reached. I haven't yet
        # tracked down the exact cases when fragments are not available (perhaps
        # very-early state trying to validate the root action group?). In any case, this
        # is just a safe guard that shouldn't break anything that I am aware of
        if len(fragments) <= 0 or len(available_choices) <= 0:
            return

        self._validate_choices(
            available_choices,
            fragments[-1],
            cursor_position=cursor_position,
        )

    def _validate_basic_param(
        self,
        action: Action,
        action_param: ActionParam,
        param_value: str,
        cursor_position: int = 0,
    ):
        """Validate a given basic (string) parameter for the parameter value.

        Args:
            action (Action): The action the given action parameter applies to
            action_param (ActionParam): The action parameter to base validation off of
            param_value (str): The value to validate against the given action parameter
            cursor_position (int, optional): The current cursor position in the prompt
                buffer. Defaults to 0.

        Raises:
            ValidationError: When the given parameter value is not valid for the current
                action parameter
        """

        assert isinstance(
            action_param.source, str
        ), f"basic param validation can only handle a string source, {action_param!r}"

        self._validate_choices(
            [action_param.source], param_value, cursor_position=cursor_position
        )

    def _validate_iterable_param(
        self,
        action: Action,
        action_param: ActionParam,
        param_value: str,
        cursor_position: int = 0,
    ):
        """Validate a given iterable (Iterable[str]) parameter for the parameter value.

        Args:
            action (Action): The action the given action parameter applies to
            action_param (ActionParam): The action parameter to base validation off of
            param_value (str): The value to validate against the given action parameter
            cursor_position (int, optional): The current cursor position in the prompt
                buffer. Defaults to 0.

        Raises:
            ValidationError: When the given parameter value is not valid for the current
                action parameter
        """

        assert isinstance(action_param.source, (list, tuple,)), (
            "iterable param validation can only handle hashable iterables, "
            f"{action_param.source!r}"
        )

        validation_choices = [choice for choice in action_param.source]
        assert all(isinstance(param_value, str) for value in validation_choices), (
            "iterable param validation can only handle hashable iterables of strings, "
            f"{validation_choices!r}"
        )

        self._validate_choices(
            validation_choices, param_value, cursor_position=cursor_position
        )

    def _validate_callable_param(
        self,
        action: Action,
        action_param: ActionParam,
        param_value: str,
        cursor_position: int = 0,
    ):
        """Validate a given callable parameter for the parameter value.

        Args:
            action (Action): The action the given parameter applies to
            action_param (ActionParam): The action parameter to base validation off of
            param_value (str): The value to validate against the given action parameter
            cursor_position (int, optional): The current cursor position in the prompt
                buffer. Defaults to 0.

        Raises:
            ValidationError: When the given parameter value is not valid for the current
                action parameter
        """

        assert callable(action_param.source), (
            "callable param validation can only handle callables that return "
            f"iterables of strings, {action_param.source!r}"
        )

        self._validate_choices(
            list(action_param.source(action)),  # type: ignore
            param_value,
            cursor_position=cursor_position,
        )

    def _validate_custom_validators(
        self,
        action: Action,
        action_param: ActionParam,
        param_value: str,
        previous_fragments: List[str],
        cursor_position: int = 0,
    ):
        """Validate any custom parameter validators for the parameter value.

        .. important::
            This validator is somewhat different than the other available private
            ``_validate_*`` methods as this requires the previous fragments that have
            appeared prior to the given action parameter's ``value``.
            This is necessary for the call to a custom callable validator (not one
            created through :meth:`~prompt_toolkit.validation.Validator.from_callable`).

        This function validates the current action parameter against custom validators
        such as those created through
        :meth:`~prompt_toolkit.validation.Validator.from_callable` or a custom callable
        that follows the following signature:

        .. code-block:: python

            def _custom_validator(
                param: ActionParam,
                param_value: str,
                previous_fragments: List[str]
            ) -> Any:
                # ... some validation logic ...
                # on failed validation a similar validation error to the following
                # should be raised
                raise prompt_toolkit.validation.ValidationError(
                    "validation error message",
                    cursor_position=0
                )

        Note that the ``param_value`` to this custom completer will **always** be the
        raw string value. We do not automatically apply whatever
        :var:`~types.ActionParam.cast` you have specified on the parameter for
        validation. We do however, pass the parameter to you in case you want to cast
        the string to a custom type yourself.

        .. note::
            The ``cursor_position`` for the raised
            :class:`~prompt_toolkit.validation.ValidationError` from a custom callable
            does not matter. Whatever validation error you raise will be caught and
            re-raised with the same error message you provide but using with the
            appropriate cursor position.

        Args:
            action (Action): The action the given parameter applies to
            action_param (ActionParam): The action parameter to base validation off of
            param_value (str): The value to validate agains the given action parameter
            previous_fragments (List[str]): The list of fragments that have appeared
                before the current given ``value`` fragment
            cursor_position (int, optional): The current cursor position in the prompt
                buffer. Defaults to 0.

        Raises:
            ValidationError: When any of the provided parameter validator callables
                raises :class:`~prompt_toolkit.validation.ValidationError`
        """

        assert action_param.validators and len(action_param.validators) > 0, (
            "Custom validation handler can only be used with action parameters using a "
            "non-empty list of validators"
        )

        for custom_validator in action_param.validators:
            if isinstance(custom_validator, Validator):
                # NOTE: we are purposefully re-raising ValidationError here so
                # we can adjust the cursor_position to properly fit the current
                # context rather than the one the custom validator from the
                # ActionParam requires
                try:
                    custom_validator.validate(
                        Document(
                            text=decode_completion(param_value),
                            cursor_position=len(param_value),
                        )
                    )
                except ValidationError as exc:
                    raise ValidationError(
                        message=exc.message, cursor_position=cursor_position
                    )
            elif callable(custom_validator):
                # Custom callable validator for utilizing the fragment history
                # in validation (since Validator can't take extra parameters and
                # that is really not its responsibility).
                #
                # Signature looks something like the following:
                #
                # custom_validator(
                #     param: ActionParam,
                #     param_value: str,
                #     previous_fragments: List[str]
                # )
                #
                # This custom validator callable should raise an instance of
                # prompt_toolkit.validation.ValidatorError on failed validation.
                # You can ignore the cursor_position parameter of the ValidationError
                # as it will always be overwritten with the proper value

                try:
                    custom_validator(
                        action_param,
                        param_value,
                        previous_fragments,
                    )
                except ValidationError as exc:
                    raise ValidationError(
                        message=exc.message, cursor_position=cursor_position
                    )
            else:
                warnings.warn(
                    f"Unsure how to handle validator {custom_validator!r}, "
                    "no validation will be performed",
                    UserWarning,
                )

    def _validate_default_validators(
        self,
        action: Action,
        action_param: ActionParam,
        param_value: str,
        cursor_position: int = 0,
    ):
        """Validate default validators for the current parameter value.

        Args:
            action (Action): The action the given parameter applies to
            action_param (ActionParam): The action parameter to base validation off of
            param_value (str): The value to validate agains the given action parameter
            cursor_position (int, optional): The current cursor position in the prompt
                buffer. Defaults to 0.

        Raises:
            ValidationError: When any of the provided parameter validator callables
                raises :class:`~prompt_toolkit.validation.ValidationError`
        """

        param_validator = None

        if isinstance(action_param.source, str):
            param_validator = self._validate_basic_param
        elif isinstance(
            action_param.source,
            (
                list,
                tuple,
            ),
        ):
            param_validator = self._validate_iterable_param
        elif callable(action_param.source):
            param_validator = self._validate_callable_param

        if param_validator:
            param_validator(
                action,
                action_param,
                decode_completion(param_value),
                cursor_position=cursor_position,
            )

    def _validate_action(
        self,
        action: Action,
        fragments: List[str],
        parent_name: str,
        cursor_position: int = 0,
    ):
        """Validate the prompt buffer fragments are valid against the given action.

        .. note::
            This validation will also raise a
            :class:`~prompt_toolkit.validation.ValidationError` when the given action
            has too few or extra values for parameters than it specifies. The only time
            this is not true is when the boolean flag ``capture_all`` set to ``True``.

            In this case, any **extra** (not missing) parameters will not fail
            validation and will instead be passed as positional arguments in the
            building of the partial action callable through the completer.

        Args:
            action (Action): The action to base validation off of
            fragments (List[str]): The current prompt buffer fragments
            parent_name (str): The name of the task that triggered the given action.
            cursor_position (int, optional): The current cursor position of the prompt
                buffer. Defaults to 0.

        Raises:
            ValidationError: When the given text fragments are not valid against the
                provided action group
            ValidationError: When there are missing or extra parameters than the action
                specifies it requires
        """

        assert (
            parent_name and len(parent_name) > 0
        ), f"parent name for action {action!r} was not given"

        if action.params is None or len(action.params) <= 0:
            return

        for param_index, (action_param, param_value) in enumerate(
            zip(action.params, fragments)
        ):
            try:
                if action_param.validators and len(action_param.validators) > 0:
                    self._validate_custom_validators(
                        action,
                        action_param,
                        decode_completion(param_value),
                        fragments[: (len(fragments) - 1) + (param_index - 1)],
                        cursor_position=cursor_position,
                    )
                else:
                    # NOTE: we don't assume any type of validation for parameters using
                    # their own completers, it is up to the user to define a custom
                    # validator for the ActionParam in this case
                    self._validate_default_validators(
                        action,
                        action_param,
                        param_value,
                        cursor_position=cursor_position,
                    )
            except ValidationError as exc:
                raise ValidationError(
                    cursor_position=cursor_position,
                    message=f"[arg: {param_index + 1!s}] {exc.message!s}",
                )

        non_empty_fragments = list(filter(None, fragments))
        compare_operator = operator.lt if action.capture_all else operator.ne
        if compare_operator(len(non_empty_fragments), len(action.params)):
            raise ValidationError(
                message=(
                    f"Invalid number of parameters for {parent_name!r}, "
                    f"expected {len(action.params)} received {len(non_empty_fragments)}"
                ),
                cursor_position=cursor_position,
            )

    def validate(self, document: Document):
        """Validate the current document from the :class:`~.completer.ActionCompleter`.

        Args:
            document (~prompt_toolkit.document.Document): The document to validate

        Raises:
            ~prompt_toolkit.validation.ValidationError: When validation of the given
                document fails.
        """

        parent, parent_name, completable, fragments = extract_context(
            self.root, get_fragments(document.text)
        )

        if isinstance(completable, ActionGroup):
            self._validate_group(
                completable,
                fragments,
                parent_name,
                cursor_position=document.cursor_position,
            )
        elif isinstance(completable, Action):
            # Validate against the current action's parent group's if an action is
            # extracted from the current document
            if completable.active is not None and not completable.active() and parent:
                self._validate_group(
                    parent,
                    fragments,
                    parent_name,
                    cursor_position=document.cursor_position,
                )
                return

            # If we don't have the action's parent name at this point, we can't really
            # safely perform validation. This should never occur, but I'm never 100%
            # confident about it
            if not parent_name:
                return

            self._validate_action(
                completable,
                fragments,
                parent_name,
                cursor_position=document.cursor_position,
            )
