# Lakebase Support Desk Submission

## Databricks App URL

`PASTE_DEPLOYED_APP_URL_HERE`

## Source code

Attach: `lakebase_support_app.zip`

## Deployed application screenshot

Insert the screenshot showing the ticket queue, selected ticket, messages, and status controls.

## Lakebase tables and sample-records screenshot

Insert the screenshot from the Lakebase SQL Editor or Tables view showing the `support_app.tickets` and `support_app.ticket_messages` records.

## Reflection

The most difficult part was configuring secure connectivity between the Databricks App service principal and Lakebase while ensuring database credentials could refresh automatically. Lakebase is designed for low-latency transactional application workloads, so it supports row-level inserts, updates, foreign keys, and persistent operational state more naturally than an analytics-focused table that is primarily optimized for large scans and batch processing. I also had to make sure the application used database-backed CRUD operations rather than temporary or hard-coded data. The next feature I would add is ticket assignment with ownership, service-level deadlines, and notifications for overdue tickets.

## Test confirmation

- Existing Lakebase tickets loaded successfully: Yes / No
- New ticket remained after refresh: Yes / No
- New message remained after refresh: Yes / No
- Updated status remained after refresh: Yes / No
