"""Module providing automatic renewals."""

import json
import re
from collections.abc import AsyncIterator
from functools import reduce
from typing import Any, NamedTuple

from folioclient import FolioClient


class Renewable(NamedTuple):
    """Represents the pair of ids needed to renew a Loan."""

    item_id: str
    patron_id: str
    source: str


def _prune_source(loan: dict[str, Any]) -> str:
    return json.dumps(
        {
            "_".join(path): reduce(
                lambda acc, key: acc.get(key) if isinstance(acc, dict) else None,
                path,
                loan,
            )
            for path in [
                ("id"),
                ("userId"),
                ("borrower", "barcode"),
                ("patronGroupAtCheckout", "name"),
                ("borrower", "patronGroup"),
                ("itemId"),
                ("item", "barcode"),
                ("item", "status", "name"),
                ("item", "instanceId"),
                ("item", "instanceHrid"),
                ("itemEffectiveLocationIdAtCheckOut"),
                ("item", "location", "name"),
                ("loanDate"),
                ("dueDate"),
                ("loanPolicy", "name"),
                ("dueDateChangedByRecall"),
                ("dueDateChangedByNearExpireUser"),
                ("dueDateChangedByHold"),
                ("status", "name"),
                ("metadata", "createdDate"),
                ("metadata", "updatedDate"),
            ]
        },
        indent=4,
        default=str,
    )


async def stream_renewables(
    client: FolioClient,
    patron_barcode_patterns: list[str],
) -> AsyncIterator[Renewable]:
    """Streams only renewable Loan information from FOLIO."""
    patron_barcode_matcher = re.compile(rf"^({r'|'.join(patron_barcode_patterns)}).*$")

    async for loan in client.folio_get_all_async(""):
        source = _prune_source(loan)

        patron_barcode = loan.get("borrower", {}).get("barcode")
        if patron_barcode is None:
            # TODO: Log the source
            continue

        if not patron_barcode_matcher.match(patron_barcode):
            # Expected because it is for another campus
            continue

        if (
            len(loan.get("itemId", "").strip()) == 0
            or len(loan.get("userId", "").strip()) == 0
        ):
            # TODO: Log the source
            continue

        if loan.get("dueDateChangedByRecall", False):
            # TODO: Log the source
            continue

        if loan.get(
            "dueDateChangedByNearExpireUser",
            False,
        ) or loan.get(
            "dueDateChangedByHold",
            False,
        ):
            # TODO: Log the source with a warning but don't skip
            ...

        yield Renewable(loan["itemId"].strip(), loan["userId"].strip(), source)


async def renew_many(client: FolioClient, renewables: AsyncIterator[Renewable]) -> None:
    """Renews until the source Loans are exhausted."""


async def renew_one(client: FolioClient, renewable: Renewable) -> None:
    """Renews an individual Loan in FOLIO."""
