"""Pydantic models mirroring Penelope's tables.

These are a faithful copy of what Penelope stores, so there are deliberately
no constraints or normalization here -- no rejecting blank ids, no stripping
whitespace, no filtering NaN readings. Any of those would mean Orion's copy
quietly disagrees with the source. Cleaning belongs at a later stage, once
there is somewhere for the cleaned data to go.

The annotations still do the error handling that matters: they are the check
that Penelope's schema has not drifted out from under us. A renamed column, an
unexpected NULL or a changed type all raise Pydantic's ValidationError, which
PenelopeClient._to_datapoints turns into a PenelopeValidationError naming the
offending row.

Two things to know before adding validation back:

    - Validators must raise ValueError or AssertionError. Pydantic folds only
      those into a ValidationError; a PenelopeValidationError raised here
      would escape the handler in client.py and lose the row it came from.
    - Unknown columns are ignored by default, so a column added upstream is
      silently left out of the copy rather than flagged.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DataType(BaseModel):
    """Mirrors a row in Penelope's `data_type` table."""
    name: str
    unit: Optional[str] = None


class DataPoint(BaseModel):
    """Mirrors a row in Penelope's `data` table."""
    dataTypeName: str
    time: datetime
    runId: str
    values: list[float]  