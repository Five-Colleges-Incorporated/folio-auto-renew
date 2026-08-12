from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from unittest import mock

import pytest
from folioclient import FolioClient
from pytest_cases import parametrize_with_cases


@dataclass
class StreamLoansTC:
    returned_loans: list[dict[str, Any]]


def _arrange(loans: list[dict[str, Any]]) -> FolioClient:
    loan_results = mock.AsyncMock()
    loan_results.__aiter__.return_value = loans
    client = mock.Mock()
    client.folio_get_all_async.return_value = loan_results

    return client


def case_no_loans() -> StreamLoansTC:
    return StreamLoansTC([])


def case_one_loan() -> StreamLoansTC:
    return StreamLoansTC(
        [
            {
                "itemId": "itemid",
                "userId": "userId",
                "borrower": {"barcode": "barcode-1234"},
            },
        ],
    )


def case_many_loans() -> StreamLoansTC:
    return StreamLoansTC(
        [
            {
                "itemId": "itemid",
                "userId": "userId",
                "borrower": {"barcode": "barcode-1234"},
            },
        ]
        * 5,
    )


@pytest.mark.asyncio
@parametrize_with_cases("tc", cases=".")
async def test_streamed_loans_count(tc: StreamLoansTC) -> None:
    from folio_auto_renew import stream_loans as uut

    client = _arrange(tc.returned_loans)

    act_loans = uut(client, [], datetime.now(tz=timezone.utc))
    assert sum([1 async for _ in act_loans]) == len(tc.returned_loans)
