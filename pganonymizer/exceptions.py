class PgAnonymizeException(Exception):
    """Base exception for all pganonymize errors."""


class InvalidFieldProvider(PgAnonymizeException):
    """Raised if an unknown field provider was used in the schema."""


class InvalidProvider(PgAnonymizeException):
    """Raised if an unknown provider class was requested."""


class InvalidProviderArgument(PgAnonymizeException):
    """Raised if an argument is unknown or invalid for a provider."""


class BadDataFormat(PgAnonymizeException):
    """Raised if the anonymized data cannot be copied."""
