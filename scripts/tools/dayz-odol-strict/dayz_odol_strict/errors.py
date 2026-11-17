class OdolStrictError(ValueError):
    def __init__(self, code, message, offset=None):
        self.code = code
        self.message = message
        self.offset = offset
        super().__init__(message)


    def __str__(self):
        suffix = "" if self.offset is None else " at byte %d" % self.offset
        return "%s%s: %s" % (self.code, suffix, self.message)
