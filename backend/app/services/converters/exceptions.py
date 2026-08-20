class ConversionError(Exception):
    pass


class InputFileNotFoundError(ConversionError):
    pass


class UnsupportedFormatError(ConversionError):
    pass


class SubprocessExecutionError(ConversionError):
    pass


class ConversionTimeoutError(ConversionError):
    pass


class OutputFileMissingError(ConversionError):
    pass


class CorruptPDFError(ConversionError):
    pass
