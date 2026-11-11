class Problem(Exception):
    """An API error: HTTP status, stable code, human message, optional extra fields for the body."""

    def __init__(self, status, code, message, **extra):
        super().__init__(message)
        self.status, self.code, self.message, self.extra = status, code, message, extra


UNEXPECTED = 'That could not be done; nothing was changed. The builder has been told what failed.'   # what the operator reads for an error nobody wrote a sentence for; the real text goes to the server log
