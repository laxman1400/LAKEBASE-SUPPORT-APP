# Lakebase Support Desk — Secret-Based Setup

This version keeps the original support-ticket assignment and adds secure secret handling for:

- A **Massive.com API key**
- A **Lakebase PostgreSQL connection URL**

Massive.com supplies the API key. **Databricks Secrets** stores both values. No API key, database password, or connection URL belongs in GitHub.

## Project files

- `app.py` — Streamlit support-ticket UI and connection test panel
- `db.py` — reads and writes support data in Lakebase using `LAKEBASE_URL`
- `massive_client.py` — makes a small authenticated Massive REST request
- `setup_secrets.py` — creates the Databricks secret scope and stores both secrets
- `app.yaml` — maps App resources to environment variables
- `verification.sql` — verifies the Lakebase tables and records
- `SUBMISSION_TEMPLATE.md` — final assignment submission template

## 1. Get a Massive.com API key

1. Sign in to Massive.com.
2. Open the Dashboard or API Keys section.
3. Copy your API key.
4. Do not paste it into any source file or GitHub setting.

## 2. Create a Lakebase password connection

1. In Databricks, open **Lakebase → Autoscaling** and create or select a project.
2. Open **Project Settings → Database connections**.
3. Enable **Password (Native Postgres roles)**. New projects have password connections disabled by default.
4. Open the production branch and go to **Roles & Databases**.
5. Select **Add role → Password**.
6. Create a role such as `support_app_role` and copy the generated password immediately.
7. In the Lakebase SQL Editor, connected as the project owner, run:

```sql
GRANT CONNECT, CREATE
ON DATABASE databricks_postgres
TO support_app_role;
```

8. Click **Connect**, choose the password role, database, and compute, and copy the PostgreSQL connection URL. It should resemble:

```text
postgresql://support_app_role:PASSWORD@HOST/databricks_postgres?sslmode=require
```

Keep the real URL private.

## 3. Create the Databricks secrets

Upload or clone this repository into a Databricks Git folder. From a Databricks Web Terminal in the project directory, run:

```bash
python setup_secrets.py
```

The script privately prompts for the two values and creates:

```text
lakebase-support-app/massive-api-key
lakebase-support-app/lakebase-url
```

It is safe to rerun; existing secret values are overwritten.

### CLI alternative

```bash
databricks secrets create-scope lakebase-support-app
databricks secrets put-secret lakebase-support-app massive-api-key
databricks secrets put-secret lakebase-support-app lakebase-url
```

The `put-secret` commands prompt for the values. Do not provide secrets as command-line arguments.

## 4. Create the Databricks App

1. Open **Databricks Apps**.
2. Create a **Custom App**.
3. Choose this Git or Workspace folder as the source.
4. Do not deploy until the two secret resources are configured.

## 5. Add the two Secret resources

In the app's **Resources** section, add the following:

### Lakebase URL secret

- Resource type: **Secret**
- Scope: `lakebase-support-app`
- Secret: `lakebase-url`
- Permission: **Can read**
- Custom resource key: `lakebase_url_secret`

### Massive API key secret

- Resource type: **Secret**
- Scope: `lakebase-support-app`
- Secret: `massive-api-key`
- Permission: **Can read**
- Custom resource key: `massive_api_key_secret`

The custom resource keys must match `app.yaml` exactly.

This version does **not** require adding Lakebase as a Database App resource because it connects using the secret PostgreSQL URL.

## 6. Deploy

Click **Deploy**. The app runtime resolves:

```yaml
LAKEBASE_URL: valueFrom lakebase_url_secret
MASSIVE_API_KEY: valueFrom massive_api_key_secret
```

On first successful launch, the app creates:

- `support_app.tickets`
- `support_app.ticket_messages`
- `support_app.app_metadata`

It also inserts three sample tickets and at least two messages for each ticket.

## 7. Test

1. Open **Connection status** in the sidebar.
2. Confirm Lakebase shows connected.
3. Click **Test Massive API**.
4. Create a support ticket.
5. Add a message.
6. Change its status.
7. Refresh the app and verify the changes remain.
8. Run `verification.sql` in Lakebase for the database screenshot.

## Troubleshooting

### `LAKEBASE_URL is missing`

Add `lakebase-support-app/lakebase-url` as an App Secret resource with custom key `lakebase_url_secret`, then redeploy.

### Password authentication failed

Confirm password connections are enabled, the URL contains the correct password, and the native role still exists on the same branch.

### Permission denied to create schema

Run the database `GRANT CONNECT, CREATE` statement as the project owner.

### Massive returns 401 or 403

Confirm the API key is current and that your Massive plan allows the test endpoint. Ticket functionality does not depend on the Massive test succeeding.

### Never commit these values

- Massive API key
- Lakebase password
- Full Lakebase PostgreSQL URL
- `.env`
