from http import HTTPStatus

from fastapi import HTTPException


class InvalidDBCredentials(HTTPException):

    def __init__(self, exc: Exception):
        self.status_code = HTTPStatus.BAD_REQUEST
        print(f"Exception: {exc}")
        self.detail = "Invalid database credentials"
        super().__init__(status_code=self.status_code, detail=self.detail)


class EmptyDatabaseError(HTTPException):

    def __init__(self, exc: Exception):
        self.status_code = HTTPStatus.NO_CONTENT
        print(f"Exception: {exc}")
        self
        super().__init__(status_code=self.status_code, detail=self.detail)
