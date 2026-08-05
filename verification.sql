-- Run these queries in the Lakebase SQL Editor after the app has launched.

SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'support_app'
ORDER BY table_name;

SELECT
    t.ticket_id,
    t.title,
    t.status,
    t.priority,
    t.category,
    t.created_by,
    t.created_at,
    COUNT(m.message_id) AS message_count
FROM support_app.tickets AS t
LEFT JOIN support_app.ticket_messages AS m
    ON m.ticket_id = t.ticket_id
GROUP BY
    t.ticket_id,
    t.title,
    t.status,
    t.priority,
    t.category,
    t.created_by,
    t.created_at
ORDER BY t.ticket_id;

SELECT
    m.message_id,
    m.ticket_id,
    t.title,
    m.author,
    m.message_text,
    m.created_at
FROM support_app.ticket_messages AS m
JOIN support_app.tickets AS t
    ON t.ticket_id = m.ticket_id
ORDER BY m.ticket_id, m.created_at, m.message_id;

-- Foreign-key verification
SELECT
    tc.constraint_name,
    kcu.table_schema,
    kcu.table_name,
    kcu.column_name,
    ccu.table_schema AS referenced_schema,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
   AND tc.constraint_schema = kcu.constraint_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
   AND ccu.constraint_schema = tc.constraint_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND kcu.table_schema = 'support_app';
