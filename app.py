"""Streamlit UI for the Lakebase-backed internal support system."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from db import (
    ALLOWED_PRIORITIES,
    ALLOWED_STATUSES,
    SCHEMA_NAME,
    add_message,
    create_ticket,
    delete_ticket,
    get_messages,
    get_ticket,
    initialize_database,
    list_tickets,
    ticket_statistics,
    update_ticket_status,
)

st.set_page_config(
    page_title="Lakebase Support Desk",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.4rem; padding-bottom: 3rem;}
      [data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 12px;
        padding: .8rem 1rem;
      }
      .ticket-meta {color: #6b7280; font-size: .9rem; margin-bottom: .6rem;}
      .message-card {
        border: 1px solid rgba(128,128,128,.22);
        border-radius: 12px;
        padding: .85rem 1rem;
        margin: .55rem 0;
      }
      .message-author {font-weight: 650;}
      .message-time {color: #6b7280; font-size: .8rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

STATUS_LABELS = {
    "open": "Open",
    "in_progress": "In progress",
    "resolved": "Resolved",
}
PRIORITY_LABELS = {"low": "Low", "medium": "Medium", "high": "High"}


@st.cache_resource(show_spinner="Connecting to Lakebase…")
def initialize_once() -> bool:
    initialize_database()
    return True


def flash(message: str, kind: str = "success") -> None:
    st.session_state["flash_message"] = (kind, message)


def show_flash() -> None:
    item = st.session_state.pop("flash_message", None)
    if not item:
        return
    kind, message = item
    getattr(st, kind, st.info)(message)


def format_time(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone().strftime("%b %d, %Y · %I:%M %p")


try:
    initialize_once()
except Exception as exc:  # Display a helpful deployment/configuration error.
    st.error("The app could not connect to or initialize Lakebase.")
    st.code(str(exc))
    with st.expander("Connection checklist"):
        st.markdown(
            """
            1. Add a **Lakebase Autoscaling database** as an App resource.
            2. Use the resource key **`postgres`** and permission **Can connect and create**.
            3. Keep `ENDPOINT_NAME` in `app.yaml` configured with `valueFrom: postgres`.
            4. Confirm the Lakebase compute is available, then redeploy the app.
            """
        )
    st.stop()

show_flash()

with st.sidebar:
    st.title("🎫 Support Desk")
    st.caption(f"Lakebase schema: `{SCHEMA_NAME}`")
    st.divider()
    st.subheader("Create a ticket")

    with st.form("create_ticket_form", clear_on_submit=True):
        new_title = st.text_input(
            "Title *", max_chars=200, placeholder="Briefly describe the issue"
        )
        new_description = st.text_area(
            "Description", max_chars=3000, placeholder="Add relevant details"
        )
        new_created_by = st.text_input(
            "Created by *", max_chars=100, placeholder="Your name"
        )
        col_priority, col_category = st.columns(2)
        with col_priority:
            new_priority = st.selectbox(
                "Priority",
                options=list(ALLOWED_PRIORITIES),
                index=1,
                format_func=lambda value: PRIORITY_LABELS[value],
            )
        with col_category:
            new_category = st.text_input(
                "Category", value="general", max_chars=50
            )
        create_submitted = st.form_submit_button(
            "Create ticket", type="primary", use_container_width=True
        )

    if create_submitted:
        try:
            created_ticket_id = create_ticket(
                title=new_title,
                description=new_description,
                created_by=new_created_by,
                priority=new_priority,
                category=new_category,
            )
            st.session_state["selected_ticket_id"] = created_ticket_id
            flash(f"Ticket #{created_ticket_id} was created.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Could not create ticket: {exc}")

st.title("Internal Support Tickets")
st.caption("All ticket and message changes are read from and written to Lakebase PostgreSQL.")

stats = ticket_statistics()
metric_columns = st.columns(5)
metric_columns[0].metric("Total", stats["total"])
metric_columns[1].metric("Open", stats["open"])
metric_columns[2].metric("In progress", stats["in_progress"])
metric_columns[3].metric("Resolved", stats["resolved"])
metric_columns[4].metric("High priority", stats["high_priority"])

st.subheader("Ticket queue")
selected_statuses = st.multiselect(
    "Filter by status",
    options=list(ALLOWED_STATUSES),
    default=list(ALLOWED_STATUSES),
    format_func=lambda value: STATUS_LABELS[value],
)

tickets = list_tickets(selected_statuses) if selected_statuses else []

if not tickets:
    st.info("No tickets match the selected status filter.")
    st.stop()

summary_rows = [
    {
        "ID": item["ticket_id"],
        "Title": item["title"],
        "Status": STATUS_LABELS[item["status"]],
        "Priority": PRIORITY_LABELS[item["priority"]],
        "Category": item["category"],
        "Created by": item["created_by"],
        "Messages": item["message_count"],
        "Updated": item["updated_at"],
    }
    for item in tickets
]

st.dataframe(
    summary_rows,
    use_container_width=True,
    hide_index=True,
    column_config={
        "ID": st.column_config.NumberColumn(format="#%d", width="small"),
        "Messages": st.column_config.NumberColumn(width="small"),
        "Updated": st.column_config.DatetimeColumn(
            format="MMM D, YYYY h:mm a", width="medium"
        ),
    },
)

ticket_lookup = {item["ticket_id"]: item for item in tickets}
ticket_ids = list(ticket_lookup)
current_selection = st.session_state.get("selected_ticket_id")
if current_selection not in ticket_lookup:
    current_selection = ticket_ids[0]

selected_index = ticket_ids.index(current_selection)
selected_ticket_id = st.selectbox(
    "Select a ticket to view",
    options=ticket_ids,
    index=selected_index,
    format_func=lambda ticket_id: (
        f"#{ticket_id} · {ticket_lookup[ticket_id]['title']} "
        f"({STATUS_LABELS[ticket_lookup[ticket_id]['status']]})"
    ),
)
st.session_state["selected_ticket_id"] = selected_ticket_id

ticket = get_ticket(selected_ticket_id)
if ticket is None:
    st.warning("This ticket was deleted. Refreshing the queue.")
    st.session_state.pop("selected_ticket_id", None)
    st.rerun()

st.divider()
details_col, activity_col = st.columns([1, 1.45], gap="large")

with details_col:
    st.subheader(f"Ticket #{ticket['ticket_id']}")
    st.markdown(f"### {ticket['title']}")
    st.markdown(
        f"<div class='ticket-meta'>Created by {ticket['created_by']} · "
        f"{format_time(ticket['created_at'])}</div>",
        unsafe_allow_html=True,
    )
    st.write(ticket["description"] or "_No description provided._")
    st.caption(
        f"Priority: {PRIORITY_LABELS[ticket['priority']]} · "
        f"Category: {ticket['category']} · Last updated: {format_time(ticket['updated_at'])}"
    )

    st.markdown("#### Update status")
    status_index = list(ALLOWED_STATUSES).index(ticket["status"])
    new_status = st.selectbox(
        "Ticket status",
        options=list(ALLOWED_STATUSES),
        index=status_index,
        format_func=lambda value: STATUS_LABELS[value],
        key=f"status_{ticket['ticket_id']}",
        label_visibility="collapsed",
    )
    if st.button(
        "Save status",
        type="primary",
        use_container_width=True,
        disabled=new_status == ticket["status"],
    ):
        try:
            update_ticket_status(ticket_id=ticket["ticket_id"], status=new_status)
            flash(
                f"Ticket #{ticket['ticket_id']} status changed to "
                f"{STATUS_LABELS[new_status]}."
            )
            st.rerun()
        except Exception as exc:
            st.error(f"Could not update status: {exc}")

    with st.expander("Delete ticket"):
        st.warning("Deleting a ticket also deletes all of its messages.")
        delete_confirmed = st.checkbox(
            f"I understand and want to delete ticket #{ticket['ticket_id']}",
            key=f"delete_confirm_{ticket['ticket_id']}",
        )
        if st.button(
            "Delete permanently",
            disabled=not delete_confirmed,
            use_container_width=True,
        ):
            try:
                deleted_id = ticket["ticket_id"]
                delete_ticket(deleted_id)
                st.session_state.pop("selected_ticket_id", None)
                flash(f"Ticket #{deleted_id} was deleted.", "warning")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not delete ticket: {exc}")

with activity_col:
    st.subheader("Messages")
    messages = get_messages(ticket["ticket_id"])

    if messages:
        for message in messages:
            safe_text = (
                message["message_text"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
            )
            safe_author = (
                message["author"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            st.markdown(
                f"""
                <div class="message-card">
                  <div class="message-author">{safe_author}</div>
                  <div class="message-time">{format_time(message['created_at'])}</div>
                  <div style="margin-top:.55rem">{safe_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No messages have been added yet.")

    st.markdown("#### Add a message")
    with st.form(f"message_form_{ticket['ticket_id']}", clear_on_submit=True):
        message_author = st.text_input(
            "Author *", max_chars=100, placeholder="Your name"
        )
        message_text = st.text_area(
            "Message *",
            max_chars=5000,
            placeholder="Add an update or reply",
            height=130,
        )
        message_submitted = st.form_submit_button(
            "Add message", type="primary", use_container_width=True
        )

    if message_submitted:
        try:
            add_message(
                ticket_id=ticket["ticket_id"],
                message_text=message_text,
                author=message_author,
            )
            flash(f"Message added to ticket #{ticket['ticket_id']}.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Could not add message: {exc}")
