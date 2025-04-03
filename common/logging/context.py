import contextvars
from collections.abc import Callable
from functools import wraps
from inspect import iscoroutinefunction, signature
from typing import Any, ParamSpec, TypeVar, cast


class LoggingContext:
    """Context variables for logging context."""

    correlation_id_var = contextvars.ContextVar("correlation_id", default="")
    labels_var = contextvars.ContextVar("labels", default={})

    @classmethod
    def set_correlation_id(cls, correlation_id: str) -> contextvars.Token:
        """Set correlation ID for the current context."""
        return cls.correlation_id_var.set(correlation_id)

    @classmethod
    def get_correlation_id(cls) -> str | None:
        """Get correlation ID for the current context, if any."""
        return cls.correlation_id_var.get()

    @classmethod
    def reset_correlation_id(cls, token: contextvars.Token) -> None:
        """Reset correlation ID using the token from set_correlation_id."""
        cls.correlation_id_var.reset(token)

    @classmethod
    def set_labels(cls, labels: dict[str, str]) -> contextvars.Token:
        """Set labels for the current context."""
        return cls.labels_var.set(labels)

    @classmethod
    def get_labels(cls) -> dict[str, str]:
        """Get labels for the current context."""
        return cls.labels_var.get()

    @classmethod
    def add_label(cls, key: str, value: str) -> contextvars.Token:
        """Add a label to the current context."""
        labels = cls.get_labels()
        labels[key] = value
        return cls.set_labels(labels)

    @classmethod
    def add_labels(cls, labels: dict[str, str]) -> contextvars.Token:
        """Add multiple labels to the current context."""
        current_labels = cls.get_labels()
        current_labels.update(labels)
        return cls.set_labels(current_labels)

    @classmethod
    def reset_labels(cls, token: contextvars.Token) -> None:
        """Reset labels using the token from set_labels."""
        cls.labels_var.reset(token)


P = ParamSpec("P")
R = TypeVar("R")


def with_context_labels(
    label_extractor: Callable[[Any], dict], param_name: str = "payload"
) -> Callable:
    """
    Decorator to manage logging context for webhook endpoints.
    Only works with async functions.

    Args:
      label_extractor: Function to extract labels from the return value of the decorated function.
      param_name: Name of the parameter that contains the payload in the decorated function.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if not iscoroutinefunction(func):
            raise TypeError(f"Function {func.__name__} must be async.")

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            webhook = None

            if param_name in kwargs:
                webhook = kwargs[param_name]
            else:
                sig = signature(func)
                param_names = list(sig.parameters.keys())
                if param_name in param_names:
                    param_idx = param_names.index(param_name)
                    if len(args) > param_idx:
                        webhook = args[param_idx]

            if not webhook:
                return await func(*args, **kwargs)

            labels = label_extractor(webhook)
            token = LoggingContext.add_labels(labels)
            try:
                return await func(*args, **kwargs)
            finally:
                LoggingContext.reset_labels(token)

        return cast(Callable[P, R], wrapper)

    return decorator
