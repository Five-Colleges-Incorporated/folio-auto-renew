"""Module providing automatic renewals."""

from collections.abc import AsyncIterator
from typing import NamedTuple

from folioclient import FolioClient


class Renewable(NamedTuple):
    """Represents the pair of ids needed to renew a Loan."""

    item_id: str
    patron_id: str
    source: str


class AutoRenew:
    """Class to provide loan renewal operations around a FolioClient."""

    def __init__(self, client: FolioClient):
        """Wraps the provide FolioClient with loan renewal operations."""
        self._client = client

    async def stream_renewables(self) -> AsyncIterator[Renewable]:
        """Streams only renewable Loan information from FOLIO."""
        for _ in range(5):
            yield Renewable("", "", "")

    async def renew_many(self, renewables: AsyncIterator[Renewable]) -> None:
        """Renews until the source Loans are exhausted."""

    async def renew_one(self, renewable: Renewable) -> None:
        """Renews an individual Loan in FOLIO."""
