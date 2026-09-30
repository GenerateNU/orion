"""Exception types raised by the Orion persistence layer.

Callers catch these instead of SQLAlchemy or Pydantic types, so the ingestion
service never has to import either library just to handle a failure. That is
the same contract penelope.exceptions makes, and it is stated twice on purpose:
the two packages sit on either side of one pipeline run, and an orchestrator
handling both should not have to learn two conventions.

They are deliberately *not* shared with the Penelope types. The orchestrator
reads from Penelope and writes to Orion in a single pass, so if both sides
raised the same connection error a retry handler could not tell "the VPN
dropped, cannot read the source" from "Neon autosuspended, cannot write the
sink". Both are retryable; the target and the remediation differ.

The split between them answers the same question Penelope's does:

    OrionConnectionError -> transient, a retry is reasonable
    everything else      -> stop, a human has to look at it
"""


class OrionError(Exception):
    """Base for every error raised by this package.

    Catch this to handle any Orion persistence failure without caring which
    kind.
    """


class OrionConnectionError(OrionError):
    """OrionDB could not be reached, or the connection dropped mid-statement.

    The only error here worth retrying. Neon autosuspends idle compute by
    default, so the first write after a quiet period failing this way is
    routine rather than exceptional -- the retry is expected to succeed once
    the endpoint has woken up.
    """


class OrionSchemaError(OrionError):
    """Connected to OrionDB, but the statement could not be run against it.

    Covers a missing table (setup_orion.py never ran), a missing grant, and
    the case where a repository's model and its table disagree about column
    names. Separate from OrionConnectionError because the connection itself
    succeeded, so retrying cannot help -- either the schema is out of step
    with the code or the role needs different permissions.
    """


class OrionValidationError(OrionError):
    """A record was rejected rather than written.

    The record did not satisfy the repository's model and the whole batch was
    abandoned before any connection was opened.

    Also covers a constraint the database enforces but the model does not: the
    row passed validation here and was still refused by Postgres, so the two
    disagree about what counts as valid.
    """
