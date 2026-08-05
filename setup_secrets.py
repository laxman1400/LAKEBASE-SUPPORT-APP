"""Create the Databricks secret scope used by the application.

Run once from a Databricks Web Terminal:

    python setup_secrets.py
"""

from __future__ import annotations

import getpass
from urllib.parse import urlparse

from databricks.sdk import WorkspaceClient

SCOPE = "lakebase-support-app"
MASSIVE_KEY = "massive-api-key"
LAKEBASE_KEY = "lakebase-url"


def ensure_scope(client: WorkspaceClient) -> None:
    existing_scopes = {
        scope.name.lower()
        for scope in client.secrets.list_scopes()
        if scope.name
    }

    if SCOPE.lower() not in existing_scopes:
        client.secrets.create_scope(scope=SCOPE)
        print(f"Created secret scope: {SCOPE}")
    else:
        print(f"Secret scope already exists: {SCOPE}")


def prompt_nonempty(message: str) -> str:
    value = getpass.getpass(message).strip()

    if not value:
        raise ValueError("Secret value cannot be empty.")

    return value


def validate_lakebase_url(lakebase_url: str) -> None:
    parsed_url = urlparse(lakebase_url)

    if parsed_url.scheme not in {"postgresql", "postgres"}:
        raise ValueError(
            "Lakebase URL must start with postgresql:// or postgres://"
        )

    if not parsed_url.username:
        raise ValueError("Lakebase URL must include a database username.")

    if not parsed_url.password:
        raise ValueError("Lakebase URL must include a database password.")

    if not parsed_url.hostname:
        raise ValueError("Lakebase URL must include a hostname.")

    if not parsed_url.path or parsed_url.path == "/":
        raise ValueError("Lakebase URL must include a database name.")


def main() -> None:
    print("Creating Databricks secrets.")
    print("Secret values will not be printed or saved in the source code.")

    massive_api_key = prompt_nonempty(
        "Paste your Massive.com API key: "
    )

    lakebase_url = prompt_nonempty(
        "Paste your Lakebase PostgreSQL URL: "
    )

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

    print("\nSecrets stored successfully:")
    print(f"{SCOPE}/{MASSIVE_KEY}")
    print(f"{SCOPE}/{LAKEBASE_KEY}")


if __name__ == "__main__":
    main()
