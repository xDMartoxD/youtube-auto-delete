"""Cache utility functions."""


def cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate cache key from prefix and arguments.

    Args:
        prefix: Key prefix
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key

    Returns:
        Generated cache key string

    Example:
        >>> cache_key("user", "123", role="admin")
        "user:123:role:admin"
    """
    parts = [prefix]
    if args:
        parts.extend(str(arg) for arg in args)
    if kwargs:
        parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    return ":".join(parts)

