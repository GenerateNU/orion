"""Domain exceptions. Services raise these; exception_handlers turns them into HTTP."""


class DomainError(Exception):
    """Base for expected errors. Anything without a specific handler becomes a 400."""


class NotFoundError(DomainError):
    def __init__(self, resource_type: str, resource_id: object):
        self.resource_type = resource_type
        self.resource_id = str(resource_id)
        super().__init__(f"{resource_type} '{resource_id}' not found")
