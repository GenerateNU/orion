"""Exception types raised by the Penelope client.

Callers catch these instead of SQLAlchemy or Pydantic types, so the ingestion
service never has to import either library just to handle a failure.

The split between them exists to answer one question for the caller: is it
worth trying again?

    PenelopeConnectionError -> transient, a retry is reasonable
    everything else         -> stop, a human has to look at it
"""


class PenelopeError(Exception):
    """Base for every error raised by this package.

    Catch this to handle any Penelope failure without caring which kind.
    """


class PenelopeConfigError(PenelopeError):
    """Required configuration is missing or malformed.

    Raised before any network access happens, so it always means the local
    environment is wrong rather than PenelopeDB being unavailable.
    """


class PenelopeConnectionError(PenelopeError):
    """PenelopeDB could not be reached, or the connection dropped mid-query.

    The only error here that is worth retrying: the usual causes (VPN down,
    timeout, connection refused) are outside our control and often temporary.
    """


class PenelopeSchemaError(PenelopeError):
    """Connected to PenelopeDB, but the data we expect is not reachable.

    Covers missing tables or columns and missing grants. Separate from
    PenelopeConnectionError because the connection itself succeeded, so
    retrying cannot help -- either the upstream schema changed or the role
    needs different permissions.
    """


class PenelopeValidationError(PenelopeError):
    """A row from PenelopeDB could not be parsed into a Pydantic model.

    Signals that Penelope's data has drifted from our models (a renamed
    column, an unexpected NULL, a malformed value), not that anything is
    wrong with the connection.
    """
