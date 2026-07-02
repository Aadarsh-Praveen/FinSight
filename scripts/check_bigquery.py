"""Verifies BigQuery connectivity and ADC auth against a public dataset table.

Usage: python scripts/check_bigquery.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from google.cloud import bigquery

TABLE = "bigquery-public-data.thelook_ecommerce.orders"


def main() -> int:
    load_dotenv()
    project = os.getenv("BIGQUERY_PROJECT")
    if not project:
        print("BIGQUERY_PROJECT is not set (check .env).", file=sys.stderr)
        return 1

    # No explicit `location=` here: bigquery-public-data datasets live in the "US"
    # multi-region, which differs from GOOGLE_CLOUD_LOCATION (e.g. us-central1, used for
    # Cloud Run). Forcing a mismatched job location causes a false "access denied".
    client = bigquery.Client(project=project)
    query = f"SELECT COUNT(*) AS row_count FROM `{TABLE}`"

    try:
        result = client.query(query).result()
    except Exception as exc:  # noqa: BLE001 - surface any auth/query failure to the user
        print(f"BigQuery query failed: {exc}", file=sys.stderr)
        return 1

    row_count = next(iter(result)).row_count
    print(f"{TABLE} row count: {row_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
