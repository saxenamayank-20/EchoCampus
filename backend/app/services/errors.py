class DomainError(Exception):
    """a business rule was broken. the message is safe to show to the user"""


class NotFoundError(DomainError):
    pass


class InvalidInputError(DomainError):
    pass


class ConflictError(DomainError):
    """something already exists, like an email"""


class PermissionDeniedError(DomainError):
    pass


class InvalidTransitionError(DomainError):
    """status change that the status machine doesn't allow"""
