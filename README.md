# FOLIO Auto Renew

An early preview of the Umbrellaleaf automatic renewals

folio-auto-renew provides a small set of async utilities to:
1. Query FOLIO for loans that meet renewal criteria.
1. Optionally filter loans by patron barcode patterns (optional).
1. Submit renewal requests through the FOLIO circulation API.

This package is intended for libraries that want to automate recurring loan renewals using institution-specific policies.

## Installation

```sh
python -m pip install folio-auto-renew
```

This library requires python 3.10+

## Usage

```python
from datetime import datetime, timezone

from folioclient import FolioClient
from folio_auto_renew import stream_loans, renew_loans

client = FolioClient(...)

renewable_loans = stream_loans(
    client=client,
    patron_barcode_patterns=None,
    due_date=datetime.now(timezone.utc),
)

await renew_loans(client, renewable_loans)
```

### Patron Barcode Filtering

Loans can be filtered to only patrons who have barcodes starting with certain prefixes.
For example:

```python
renewable_loans = stream_loans(
    client=client,
    patron_barcode_patterns=[
        "2112",
        "3335",
    ],
    due_date=cutoff_date,
)
```

Passing None disables barcode filtering and processes all matching loans.

### Customizing the base CQL query

The default query to identify loans is intended to be used by Five Colleges.
Most libraries will need to replace this query before using the package.

The template is exposed as `RENEWABLES_QUERY_TEMPLATE` and can be replaced like this:
```python
import folio_auto_renew

folio_auto_renew.RENEWABLES_QUERY_TEMPLATE = (
    'status="Open" '
    'AND itemStatus=="Checked Out" '
    'AND loanPolicyId=="<your-loan-policy-id>" '
    'AND dueDate<="{:%Y-%m-%dT%H:00:00%z}" '
    'sortBy id/sort.ascending'
)
```

It is important to preserve the due-date format placeholder so the cutoff date can be injected correctly.
