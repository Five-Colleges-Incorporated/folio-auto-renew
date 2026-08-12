from datetime import datetime, timezone
from typing import Any
from unittest import mock

import pytest
from folioclient import FolioClient
from pytest_cases import parametrize_with_cases


def _arrange(loans: list[dict[str, Any]]) -> FolioClient:
    loan_results = mock.AsyncMock()
    loan_results.__aiter__.return_value = loans
    client = mock.Mock()
    client.folio_get_all_async.return_value = loan_results

    return client


def case_no_loans() -> list[dict[str, Any]]:
    return []


def case_one_loan() -> list[dict[str, Any]]:
    return [
        {
            "itemId": "itemid",
            "userId": "userId",
            "borrower": {"barcode": "barcode-1234"},
        },
    ]


def case_many_loans() -> list[dict[str, Any]]:
    return [
        {
            "itemId": "itemid",
            "userId": "userId",
            "borrower": {"barcode": "barcode-1234"},
        },
    ] * 5


@pytest.mark.asyncio
@parametrize_with_cases("exp_loans", cases=".")
async def test_streamed_loans_count(exp_loans: list[dict[str, Any]]) -> None:
    from folio_auto_renew import stream_loans as uut

    client = _arrange(exp_loans)

    act_loans = uut(client, [], datetime.now(tz=timezone.utc))
    assert sum([1 async for _ in act_loans]) == len(exp_loans)
