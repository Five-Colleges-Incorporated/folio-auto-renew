from datetime import datetime, timezone
from unittest import mock

import pytest


@pytest.mark.asyncio
async def test_no_loans() -> None:
    from folio_auto_renew import stream_loans as uut

    loan_results = mock.AsyncMock()
    loan_results.__aiter__.return_value = []
    client = mock.Mock()
    client.folio_get_all_async.return_value = loan_results

    loans = uut(client, [], datetime.now(tz=timezone.utc))
    assert sum([1 async for _ in loans]) == 0


@pytest.mark.asyncio
async def test_one_loan() -> None:
    from folio_auto_renew import stream_loans as uut

    loan_results = mock.AsyncMock()
    loan_results.__aiter__.return_value = [
        {
            "itemId": "itemid",
            "userId": "userId",
            "borrower": {"barcode": "barcode-1234"},
        },
    ]
    client = mock.Mock()
    client.folio_get_all_async.return_value = loan_results

    loans = uut(client, ["barcode"], datetime.now(tz=timezone.utc))
    assert sum([1 async for _ in loans]) == 1


@pytest.mark.asyncio
async def test_many_loans() -> None:
    from folio_auto_renew import stream_loans as uut

    loan_results = mock.AsyncMock()
    loan_results.__aiter__.return_value = [
        {
            "itemId": "itemid",
            "userId": "userId",
            "borrower": {"barcode": "barcode-1234"},
        },
    ] * 5
    client = mock.Mock()
    client.folio_get_all_async.return_value = loan_results

    loans = uut(client, ["barcode"], datetime.now(tz=timezone.utc))
    assert sum([1 async for _ in loans]) == 5
