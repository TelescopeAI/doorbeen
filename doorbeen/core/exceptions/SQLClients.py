from doorbeen.core.assistants.analysis.sql.query.validation import ValidationResult


class CSQLInvalidQuery(Exception):

    def __init__(self, e: Exception):
        self.message = e.args[0]
        super().__init__(self.message)


class QueryValidationFailed(Exception):
    def __init__(self, validation: ValidationResult):
        self.message = validation.explanation
        super().__init__(self.message)
