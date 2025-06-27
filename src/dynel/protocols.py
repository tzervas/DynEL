"""
Protocols for DynEL's extensible components.

This module defines protocol classes that enable a pluggable architecture
for formatters, handlers, and potentially other aspects of DynEL.
These follow modern Python typing practices, including PEP 695 generic syntax.
"""
from typing import Any, Protocol, runtime_checkable

# PEP 695 generic type parameter syntax is used directly in class definitions.
# For example: class LogFormatter[T](Protocol):
# For ExceptionHandler, E is bound to Exception: class ExceptionHandler[E: Exception](Protocol):

@runtime_checkable
class LogFormatter[T](Protocol):
    """
    Protocol for extensible log formatting.

    A LogFormatter is responsible for taking a log record of a generic type ``T``
    and converting it into a string representation or a serializable dictionary.
    """
    def format(self, record: T) -> str:
        """
        Formats the log record into a string.

        :param record: The log record to format.
        :type record: T
        :return: A string representation of the log record.
        :rtype: str
        """
        ...

    def serialize(self, record: T) -> dict[str, Any]:
        """
        Serializes the log record into a dictionary.

        This is typically used for structured logging formats like JSON.

        :param record: The log record to serialize.
        :type record: T
        :return: A dictionary representation of the log record.
        :rtype: dict[str, Any]
        """
        ...

@runtime_checkable
class ExceptionHandler[E: Exception](Protocol):
    """
    Protocol for pluggable exception handlers.

    An ExceptionHandler can determine if it can handle a given exception
    and then perform actions to handle it, such as logging it, modifying it,
    or triggering other processes.
    The generic type ``E`` is bound to :class:`Exception`, meaning handlers
    are typed to the specific exceptions they can process.
    """
    def can_handle(self, exc: E) -> bool:
        """
        Determines if this handler can process the given exception.

        :param exc: The exception instance to check.
        :type exc: E
        :return: True if the handler can process the exception, False otherwise.
        :rtype: bool
        """
        ...

    def handle(self, exc: E, context: dict[str, Any]) -> None:
        """
        Handles the given exception.

        This method is called if `can_handle` returns True for the exception.
        It should contain the logic for processing the exception (e.g., logging,
        transforming, notifying).

        :param exc: The exception instance to handle.
        :type exc: E
        :param context: Additional context information that might be relevant
                        for handling the exception.
        :type context: dict[str, Any]
        :return: None
        """
        ...
