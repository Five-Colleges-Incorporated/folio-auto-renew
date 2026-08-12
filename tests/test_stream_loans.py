from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TypeAlias
from unittest import mock
from uuid import uuid4

import pytest
from folioclient import FolioClient
from pytest_cases import parametrize, parametrize_with_cases

from folio_auto_renew import RenewableLoan
from folio_auto_renew import stream_loans as uut

Loan: TypeAlias = dict[str, Any]


@dataclass
class StreamLoansTC:
    returned_loans: list[Loan]
    expected_loans: list[RenewableLoan]
    barcode_patterns: list[str] = field(default_factory=list)

    @staticmethod
    def generate_loan(barcode: str = "barcode") -> Loan:
        return {
            "itemId": str(uuid4()).split("-")[0],
            "userId": str(uuid4()).split("-")[0],
            "borrower": {"barcode": barcode},
        }

    def arrange_client(self) -> FolioClient:
        loan_results = mock.AsyncMock()
        loan_results.__aiter__.return_value = self.returned_loans
        client = mock.Mock()
        client.folio_get_all_async.return_value = loan_results

        return client


@parametrize("loan_count", [0, 1, 5])
def case_ok_nobarcode(loan_count: int) -> StreamLoansTC:
    returned_loans = [StreamLoansTC.generate_loan() for _ in range(loan_count)]
    return StreamLoansTC(
        returned_loans,
        [RenewableLoan(loan["itemId"], loan["userId"], "") for loan in returned_loans],
    )


@pytest.mark.asyncio
@parametrize_with_cases("tc", cases=".")
async def test_streamed_loans(tc: StreamLoansTC) -> None:
    actual_loans = uut(
        tc.arrange_client(),
        tc.barcode_patterns,
        datetime.now(tz=timezone.utc),
    )
    assert [loan async for loan in actual_loans] == tc.expected_loans
