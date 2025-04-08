from http import HTTPStatus
from typing import Optional

from doorbeen.core.types.ts_model import TSModel


class ErrorJSON(TSModel):
    """ This class is used to generate JSON error messages for the API.
    :param code: The error code.
    :param status: The HTTP status code.
    :param description: The error description.
    :param suggestion: The suggestion to resolve the error.

    :type code: str
    :type status: HTTPStatus
    :type description: str
    :type suggestion: Optional[str]

    :return: A JSON error message.
    """
    code: str
    status: HTTPStatus
    description: str
    suggestion: Optional[str]

    def generate(self):
        """
        This method is used to generates a JSON error message for the API.
        :return: A JSON error message.
        """
        return self.json()
