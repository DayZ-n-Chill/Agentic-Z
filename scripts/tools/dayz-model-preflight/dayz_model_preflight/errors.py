class PreflightError(ValueError):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


    def __str__(self):
        return "%s: %s" % (self.code, self.message)
