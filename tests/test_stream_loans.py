from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TypeAlias
from unittest import mock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
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
            "id": str(uuid4()),
            "itemId": str(uuid4()),
            "userId": str(uuid4()),
            "borrower": {"barcode": barcode},
        }

    def arrange_client(self) -> mock.MagicMock:
        loan_results = mock.AsyncMock()
        loan_results.__aiter__.return_value = self.returned_loans
        client = mock.Mock()
        client.folio_get_all_async.return_value = loan_results

        return client


@parametrize("loan_count", [0, 1, 5])
def case_nobarcodefilter(loan_count: int) -> StreamLoansTC:
    returned_loans = [StreamLoansTC.generate_loan() for _ in range(loan_count)]
    return StreamLoansTC(
        returned_loans,
        [RenewableLoan(loan["itemId"], loan["userId"], "") for loan in returned_loans],
    )


def case_one_barcodefilter() -> StreamLoansTC:
    returned_loans = []
    expected_loans = []

    def expect_last_returned_loan() -> None:
        expected_loans.append(
            RenewableLoan(
                returned_loans[-1]["itemId"],
                returned_loans[-1]["userId"],
                "",
            ),
        )

    returned_loans.append(StreamLoansTC.generate_loan(""))
    returned_loans.append(StreamLoansTC.generate_loan("nb111"))
    returned_loans.append(StreamLoansTC.generate_loan(" mbtrim"))
    expect_last_returned_loan()
    returned_loans.append(StreamLoansTC.generate_loan("mb1111"))
    expect_last_returned_loan()
    returned_loans.append(StreamLoansTC.generate_loan("mb"))
    expect_last_returned_loan()
    returned_loans.append(StreamLoansTC.generate_loan("123mb"))

    return StreamLoansTC(returned_loans, expected_loans, ["mb"])


def case_multiple_barcodefilters() -> StreamLoansTC:
    returned_loans = []
    expected_loans = []

    def expect_last_returned_loan() -> None:
        expected_loans.append(
            RenewableLoan(
                returned_loans[-1]["itemId"],
                returned_loans[-1]["userId"],
                "",
            ),
        )

    returned_loans.append(StreamLoansTC.generate_loan(""))
    returned_loans.append(StreamLoansTC.generate_loan(" nbtrim"))
    expect_last_returned_loan()
    returned_loans.append(StreamLoansTC.generate_loan("nb111"))
    expect_last_returned_loan()
    returned_loans.append(StreamLoansTC.generate_loan("123nb"))
    returned_loans.append(StreamLoansTC.generate_loan("nmb"))
    returned_loans.append(StreamLoansTC.generate_loan("mnb"))
    returned_loans.append(StreamLoansTC.generate_loan(" mbtrim"))
    expect_last_returned_loan()
    returned_loans.append(StreamLoansTC.generate_loan("mb1111"))
    expect_last_returned_loan()
    returned_loans.append(StreamLoansTC.generate_loan("mb"))
    expect_last_returned_loan()
    returned_loans.append(StreamLoansTC.generate_loan("123mb"))

    return StreamLoansTC(returned_loans, expected_loans, ["mb", "nb"])


def case_mangled_loans() -> StreamLoansTC:
    returned_loans = []

    returned_loans.append(StreamLoansTC.generate_loan())
    del returned_loans[-1]["id"]
    returned_loans.append(StreamLoansTC.generate_loan())
    del returned_loans[-1]["userId"]
    returned_loans.append(StreamLoansTC.generate_loan())
    del returned_loans[-1]["itemId"]

    return StreamLoansTC(returned_loans, [])


@parametrize(
    "has_barcode_patterns",
    [True, False],
    ids=["has_patterns", "no_patterns"],
)
def case_borrower_missing(has_barcode_patterns: bool) -> StreamLoansTC:
    returned_loans = []
    expected_loans = []

    def expect_last_returned_loan() -> None:
        expected_loans.append(
            RenewableLoan(
                returned_loans[-1]["itemId"],
                returned_loans[-1]["userId"],
                "",
            ),
        )

    returned_loans.append(StreamLoansTC.generate_loan("mb"))
    del returned_loans[-1]["borrower"]
    if not has_barcode_patterns:
        expect_last_returned_loan()
    returned_loans.append(StreamLoansTC.generate_loan("mb"))
    del returned_loans[-1]["borrower"]["barcode"]
    if not has_barcode_patterns:
        expect_last_returned_loan()

    return StreamLoansTC(
        returned_loans,
        expected_loans,
        ["mb"] if has_barcode_patterns else [],
    )


def case_due_date_changed() -> StreamLoansTC:
    returned_loans = []
    expected_loans = []

    def expect_last_returned_loan() -> None:
        expected_loans.append(
            RenewableLoan(
                returned_loans[-1]["itemId"],
                returned_loans[-1]["userId"],
                "",
            ),
        )

    returned_loans.append(StreamLoansTC.generate_loan())
    returned_loans[-1]["dueDateChangedByRecall"] = True
    returned_loans.append(StreamLoansTC.generate_loan())
    returned_loans[-1]["dueDateChangedByRecall"] = False
    expect_last_returned_loan()
    returned_loans.append(StreamLoansTC.generate_loan())
    returned_loans[-1]["dueDateChangedByNearExpireUser"] = True
    expect_last_returned_loan()
    returned_loans.append(StreamLoansTC.generate_loan())
    returned_loans[-1]["dueDateChangedByHold"] = True
    expect_last_returned_loan()

    return StreamLoansTC(returned_loans, expected_loans)


@pytest.mark.asyncio
@parametrize_with_cases("tc", cases=".")
async def test_cleansfilters_loans(tc: StreamLoansTC) -> None:
    actual_loans = uut(
        tc.arrange_client(),
        tc.barcode_patterns,
        datetime.now(tz=timezone.utc),
    )
    assert [loan async for loan in actual_loans] == tc.expected_loans


async def test_duedate() -> None:
    client = StreamLoansTC([], []).arrange_client()

    duedate = datetime(2026, 4, 1, 13, 14, 15, tzinfo=ZoneInfo("America/New_York"))
    async for _ in uut(client, [], duedate):
        # We have to actual enumerate the list to get the call to happen
        ...

    client.folio_get_all_async.assert_called_once()
    # daylight savings...
    assert (
        "2026-04-01T13:00:00-0400"
        in client.folio_get_all_async.call_args_list[0][1]["query"]
    ) or (
        "2026-04-01T13:00:00-0500"
        in client.folio_get_all_async.call_args_list[0][1]["query"]
    )
