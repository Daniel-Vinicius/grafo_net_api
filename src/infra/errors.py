class ConflictError(Exception):
    """A conflicting operation that the caller can resolve."""


class UnavailableError(Exception):
    """A technical dependency is temporarily unavailable."""
