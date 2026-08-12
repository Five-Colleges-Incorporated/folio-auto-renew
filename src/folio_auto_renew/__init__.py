"""Module providing automatic renewals."""

import json
import re
from collections.abc import AsyncIterator
from datetime import datetime
from functools import reduce
from typing import Any, NamedTuple

from folioclient import FolioClient, FolioError


class RenewableLoan(NamedTuple):
    """Represents the pair of ids needed to renew a Loan."""

    item_id: str
    patron_id: str
    source: str


async def stream_loans(
    client: FolioClient,
    patron_barcode_patterns: list[str],
    due_date: datetime,
) -> AsyncIterator[RenewableLoan]:
    """Streams only renewable Loan information from FOLIO."""
    patron_barcode_matcher = re.compile(rf"^({r'|'.join(patron_barcode_patterns)}).*$")
    renewables_query = RENEWABLES_QUERY_TEMPLATE.format(due_date)
    # TODO: Log the matcher.pattern and renewables_query

    async for loan in client.folio_get_all_async(
        path="/circulation/loans",
        key="loans",
        query=renewables_query,
    ):
        source = _printable_loan(loan)

        if (
            not isinstance(patron := loan.get("borrower", {}), dict)
            or (patron_barcode := patron.get("barcode")) is None
        ):
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

        yield RenewableLoan(loan["itemId"].strip(), loan["userId"].strip(), source)


async def renew_loans(
    client: FolioClient,
    renewables: AsyncIterator[RenewableLoan],
) -> None:
    """Renews until the source Loans are exhausted."""
    async for loan in renewables:
        # TODO: Verbosely log Renewing: ids

        try:
            new_loan = await client.folio_post_async(
                "/circulation/renew-by-id",
                payload={
                    "itemId": loan.item_id,
                    "userId": loan.patron_id,
                },
            )
            if new_loan is not None:
                # TODO: Verbosely log Renewed: _printable_loan(new_loan)
                ...
        except FolioError as fe:
            f"""TODO: Log {fe} and the source as error"""


RENEWABLES_QUERY_TEMPLATE = (
    'status="Open" AND itemStatus=="Checked Out" '
    # 12-month-unlimited
    'AND loanPolicyId=="9089d8ff-decd-401c-a4dd-61053efefdb6" '
    # Staff and Faculty
    "AND patronGroupIdAtCheckout=="
    "("
    '"612512f9-b2f1-4716-9c2a-463b484b0613" '
    'OR "4261cb0a-edf6-4302-8028-9e5b67050c9e"'
    ") "
    # Hampshire Locations
    "NOT itemEffectiveLocationIdAtCheckOut=="
    "("
    '"31f0608e-bb2e-45d9-bdbc-db47570a2869" '
    'OR "fa192f01-6cbc-4c2b-bc6f-fa2c3662ac11" '
    'OR "2b267012-9f0b-4a7c-b35c-50f2e87d04ab" '
    'OR "58c0b718-13c6-4895-89bc-4cfaa380f4ea" '
    'OR "8b72b22f-616d-45a9-b83b-ba539f3200b4" '
    'OR "0169bb12-10b2-495b-ba6c-5e70a379c802" '
    'OR "f991b513-c0f0-444e-b566-f5e878e08c18" '
    'OR "f68d3012-d2ce-49b7-93eb-cc3bce7e20c9" '
    'OR "b241fe21-2931-42e0-bd09-57c63cfca7eb" '
    'OR "2e3d20b1-8c1b-4bf3-a3e9-8725414898f0" '
    'OR "3ca8cbd4-5460-448a-b7d8-e6f067afb748" '
    'OR "7b555ddf-4d94-4dd8-bd9e-294ad5fc786f" '
    'OR "1ca4f6b6-2e1c-442c-bfc6-764b285e8f7a" '
    'OR "dcfef97d-3340-4f48-a1bc-ac25fad65c6f" '
    'OR "7a3bf545-0fa7-4588-a10e-9ae79895cb29" '
    'OR "401a6760-7233-416a-bac0-cdc58efb39ab" '
    'OR "0add1d37-ddb7-4a7e-8fd1-41f7e39bc303" '
    'OR "3e11f4b0-9b95-4866-9030-fa5c9a441a45" '
    'OR "cbf101a9-6035-4fb0-b62e-e4a5ea1736aa" '
    'OR "657fc0a9-0e03-4b6c-8b10-8c086aa41fba" '
    'OR "c5cc5b04-d85b-44a1-94d9-afbd1fc7da73" '
    'OR "89bde59a-5f96-402a-a771-d8d3348cc774" '
    'OR "9c25b803-267e-43ad-afbb-aefa5be351e4" '
    'OR "437ce3fd-7a6e-48df-a332-826cfa2135dd" '
    'OR "0671c97b-80a6-419d-a91b-ceaab672ccac" '
    'OR "002d8042-9caa-4e33-add2-6c3013e4b8c7" '
    'OR "50e9849f-ebef-4306-adb0-c0f8d62400fe" '
    'OR "94ee5463-a30a-4b37-a630-7df934a5f731" '
    'OR "2010ae0f-e4c0-412b-bd01-b6af582c59c6"'
    ") "
    'AND dueDate<="{:%Y-%m-%dT%H:00:00%z}" '
    "sortBy id/sort.ascending"
)


def _printable_loan(loan: dict[str, Any]) -> str:
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
