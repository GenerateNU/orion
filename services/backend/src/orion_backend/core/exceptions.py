"""Domain exceptions. Services raise these; exception_handlers turns them into HTTP."""


class DomainError(Exception):
    """Base for expected errors. Anything without a specific handler becomes a 400."""


class NotFoundError(DomainError):
    def __init__(self, resource_type: str, resource_id: object):
        self.resource_type = resource_type
        self.resource_id = str(resource_id)
        super().__init__(f"{resource_type} '{resource_id}' not found")


class AlreadyExistsError(DomainError):
    def __init__(self, resource_type: str, resource_id: object):
        super().__init__(f"{resource_type} '{resource_id}' already exists")


class ConflictError(DomainError):
    """The request clashes with current state, e.g. a run already being processed (409)."""


class InvalidParameterError(DomainError):
    """A request parameter is well-formed but not allowed (422)."""


class UpstreamError(DomainError):
    """A service we depend on (e.g. Penelope off VPN) failed or was unreachable (502)."""

    def __init__(self, upstream: str, reason: object = None):
        self.upstream = upstream
        message = f"{upstream} is unreachable"
        super().__init__(f"{message}: {reason}" if reason else message)


class ServiceUnavailableError(DomainError):
    """A dependency isn't configured on this deployment (503)."""
