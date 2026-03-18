class DomainError(Exception):
    status_code: int = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class EntityNotFoundError(DomainError):
    status_code = 404


class EntityBadDataError(DomainError):
    status_code = 403


class OperationFailedError(DomainError):
    status_code = 400
