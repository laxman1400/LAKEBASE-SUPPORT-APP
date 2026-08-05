# Lakebase Support Desk — Databricks App

A small Streamlit application for creating support tickets, adding messages, and updating ticket status. All operational data is stored in Lakebase PostgreSQL; the interface contains no hard-coded ticket list.

## Included requirements

- Related `tickets` and `ticket_messages` tables with a PostgreSQL foreign key
- Three sample tickets and two messages per ticket
- Open, in-progress, and resolved statuses
- View and filter tickets
- View messages for a selected ticket
- Create tickets
- Add ticket messages
- Update ticket status
- Persistent writes after page refresh

## Bonus features

- Priority and category
- Status filtering
- Input validation and useful errors
- Ticket statistics
- Delete with explicit confirmation
- Styled Streamlit interface

## Project files

- `app.py` — Streamlit interface
- `db.py` — Lakebase connection, schema initialization, seed data, and CRUD operations
- `app.yaml` — Databricks App runtime configuration
- `requirements.txt` — Python dependencies
- `verification.sql` — Queries for validating tables, records, and the foreign key
- `SUBMISSION_TEMPLATE.md` — Final response template

## Deploy in Databricks

### 1. Create Lakebase

1. Open the Databricks app switcher and choose **Lakebase Postgres**.
2. Create a Lakebase **Autoscaling** project.
3. Keep or create a database such as `databricks_postgres`.
4. Confirm the production branch and compute are available.

### 2. Create the Databricks App

1. Open **Databricks Apps** and select **Create app**.
2. Create a custom app, or start from a Streamlit template.
3. In **App resources**, add **Database → Lakebase Autoscaling**.
4. Select the project, branch, and database created above.
5. Choose **Can connect and create**.
6. Set the resource key to exactly **`postgres`**.

The database resource automatically supplies `PGHOST`, `PGDATABASE`, `PGPORT`, `PGSSLMODE`, and `PGUSER`. The `app.yaml` file maps the same resource to `ENDPOINT_NAME`, which the Databricks SDK uses to obtain rotating OAuth credentials.

### 3. Upload the source

Upload the unzipped folder to a Databricks Workspace folder, then choose that folder as the app deployment source.

CLI alternative:

```bash
databricks sync . /Workspace/Users/<your-email>/lakebase-support-app

databricks apps deploy <your-app-name> \
  --source-code-path /Workspace/Users/<your-email>/lakebase-support-app
```

### 4. Launch and initialize

Open the deployed app URL. On first launch, the app service principal creates the `support_app` schema, its tables and indexes, and the sample records. The sample data is marked as seeded, so it is not inserted again on later refreshes or redeployments.

### 5. Test persistence

Complete these actions in the deployed app:

1. Confirm the three sample tickets load.
2. Create a ticket with your name.
3. Select that ticket and add a message.
4. Change its status from Open to In progress or Resolved.
5. Refresh the browser and confirm the ticket, message, and status remain.

### 6. Capture submission screenshots

**Application screenshot:** select a ticket so the screenshot shows the ticket queue, statistics, ticket details, messages, and status control.

**Lakebase screenshot:** open the Lakebase SQL Editor and run `verification.sql`. Capture the result showing the three sample tickets and message counts. A second result can show `ticket_messages` records and the `ticket_id` relationship.

## Troubleshooting

### Missing `ENDPOINT_NAME`

Edit the app resource and confirm its key is `postgres`, then redeploy. `app.yaml` uses `valueFrom: postgres`.

### Missing PG environment variables

Confirm the Lakebase database was added under the app's **Resources** section and that the app was redeployed after adding it.

### Permission denied when creating the schema

The app resource must have **Can connect and create**, and the person adding it must have sufficient permission on the Lakebase project.

### App connects but later receives an authentication error

Keep `databricks-sdk>=0.81.0`. The connection class creates a fresh OAuth token for every new pooled connection and recycles connections before the one-hour token lifetime.

## Local testing option

For local OAuth testing, authenticate the Databricks CLI and set the Lakebase connection values. Use your Databricks user identity as `PGUSER` and set `ENDPOINT_NAME` to the Lakebase compute resource path.

```bash
databricks auth login
export PGHOST="<lakebase-host>"
export PGDATABASE="databricks_postgres"
export PGUSER="your.email@company.com"
export PGPORT="5432"
export PGSSLMODE="require"
export ENDPOINT_NAME="projects/<project-id>/branches/<branch-id>/endpoints/<endpoint-id>"
pip install -r requirements.txt
streamlit run app.py
```

For native PostgreSQL password testing instead, omit `ENDPOINT_NAME` and set `PGPASSWORD`.
