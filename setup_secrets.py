"""Create the Databricks secret scope used by this application.

Run this once from a Databricks Web Terminal or another environment where
WorkspaceClient authentication is already configured:

    python setup_secrets.py

The script never prints either secret value.
"""

from __future__ import annotations

import getpass
import sys
from urllib.parse import urlparse

from databricks.sdk import WorkspaceClient

SCOPE = "lakebase-support-app"
MASSIVE_KEY = "massive-api-key"
LAKEBASE_KEY = "lakebase-url"


def ensure_scope(client: WorkspaceClient) -> None:
    existing = {item.name.lower() for item in client.secrets.list_scopes()}
    if SCOPE.lower() not in existing:
        client.secrets.create_scope(scope=SCOPE)
        print(f"Created secret scope: {SCOPE}")
    else:
        print(f"Secret scope already exists: {SCOPE}")


def prompt_nonempty(label: str) -> str:
    value = getpass.getpass(label).strip()
    if not value:
        raise ValueError("A non-empty value is required.")
    return value


def validate_lakebase_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError("Lakebase URL must begin with postgresql:// or postgres://")
    if not parsed.hostname or not parsed.username or not parsed.password:
        raise ValueError("Lakebase URL must include role, password, host, and database.")
    if not parsed.path or parsed.path == "/":
        raise ValueError("Lakebase URL must include the database name.")


def main() -> int:
    print("This creates Databricks secrets; nothing is written to the source files.")
    massive_api_key = prompt_nonempty("Paste your Massive.com API key: ")
    lakebase_url = prompt_nonempty("Paste your Lakebase PostgreSQL URL: ")
    validate_lakebase_url(lakebase_url)

    client = WorkspaceClient()
    ensure_scope(client)
    client.secrets.put_secret(
        scope=SCOPE,
        key=MASSIVE_KEY,
        string_value=massive_api_key,
    )
    client.secrets.put_secret(
        scope=SCOPE,
        key=LAKEBASE_KEY,
        string_value=lakebase_url,
    )

    print("Stored secrets successfully:")
    print(f"  {SCOPE}/{MASSIVE_KEY}")
    print(f"  {SCOPE}/{LAKEBASE_KEY}")
    print("Next: add both secrets to the Databricks App as Secret resources.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
