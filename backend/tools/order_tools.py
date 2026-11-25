# isort: skip_file
# ruff: noqa: E402
"""
order_tools.py
--------------
MongoDB helper + LangGraph node for order lookup.

Public surface
--------------
get_order_details(order_id)  – low-level MongoDB query, returns dict or None
order_lookup(state)          – LangGraph node; stores result in state["order_details"]

Order document shape (from models.ORDERS_SCHEMA)
-------------------------------------------------
{
    "order_id":      str,
    "customer_id":   str,
    "product":       str,
    "amount":        int | float | Decimal128,
    "delivery_date": datetime,
    "status":        "pending" | "processing" | "shipped" | "delivered" | "cancelled",
    "created_at":    datetime   (optional)
}

Workflow routing
----------------
  order found  → current_step = "customer_history"  (next node in graph)
  order missing → case_status  = "order_not_found"   → graph routes to handle_failure
"""
from __future__ import annotations

import os
import sys

# Ensure the backend/ directory is on sys.path so that sibling packages
# (database, agents, tools) are importable regardless of launch location.
# This MUST come BEFORE any local package imports.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Any  # noqa: E402

from pymongo.errors import PyMongoError  # noqa: E402

from agents.state import RefundState  # noqa: E402
from database.models import get_orders_col  # noqa: E402


# ---------------------------------------------------------------------------
# MongoDB helper
# ---------------------------------------------------------------------------

def get_order_details(order_id: str) -> dict[str, Any] | None:
    """
    Fetch a single order document from MongoDB by its ``order_id`` field.

    Parameters
    ----------
    order_id:
        The unique order identifier to look up (e.g. ``"ORD-20240001"``).

    Returns
    -------
    dict
        The order document (with ``_id`` removed for JSON safety) if found.
    None
        When no document matches *order_id*, or a database error occurs.

    Raises
    ------
    Does **not** raise – all ``PyMongoError`` exceptions are caught and
    ``None`` is returned so that the caller (the LangGraph node) can decide
    how to handle the failure gracefully.
    """
    try:
        col = get_orders_col()
        doc = col.find_one({"order_id": order_id}, {"_id": 0})
        return doc  # None when not found
    except PyMongoError as exc:
        # Log to stderr so the exception is visible in server logs without
        # crashing the workflow.
        import sys
        print(f"[order_tools] MongoDB error for order_id={order_id!r}: {exc}",
              file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def order_lookup(state: RefundState) -> dict:
    """
    LangGraph node: look up the order and store its details in the state.

    Reads
    -----
    state["order_id"]   – set by validate_request

    Writes (returned partial state — merged by LangGraph into RefundState)
    -----------------------------------------------------------------------
    order_details  → dict  (order found)  |  None (not found)
    case_status    → "order_not_found"    |  "in_progress"
    current_step   → "order_lookup"       |  "customer_history"
    errors         → appended on failure
    """

    order_id: str = (state.get("order_id") or "").strip()
    errors: list[str] = list(state.get("errors") or [])

    # ------------------------------------------------------------------ #
    # Guard: order_id must be present
    # ------------------------------------------------------------------ #
    if not order_id:
        errors.append(
            "order_lookup: 'order_id' is missing from state. "
            "Make sure validate_request ran successfully before this node."
        )
        return {
            "order_details": None,
            "case_status": "order_not_found",
            "current_step": "order_lookup",
            "errors": errors,
        }

    # ------------------------------------------------------------------ #
    # Call the MongoDB helper
    # ------------------------------------------------------------------ #
    order: dict[str, Any] | None = get_order_details(order_id)

    # ------------------------------------------------------------------ #
    # Order NOT found (or DB error)
    # ------------------------------------------------------------------ #
    if order is None:
        errors.append(
            f"Order '{order_id}' was not found in the system. "
            "Please verify the order ID and try again. "
            "The refund workflow cannot proceed without a valid order."
        )
        return {
            "order_details": None,
            "case_status": "order_not_found",
            "current_step": "order_lookup",
            "errors": errors,
        }

    # ------------------------------------------------------------------ #
    # Order found — serialize any non-JSON-safe types and update state
    # ------------------------------------------------------------------ #
    serialized_order: dict[str, Any] = _serialize_order(order)

    return {
        "order_details": serialized_order,   # → state["order_details"]
        "case_status": "in_progress",
        "current_step": "customer_history",
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Internal serialisation helper
# ---------------------------------------------------------------------------

def _serialize_order(order: dict[str, Any]) -> dict[str, Any]:
    """
    Convert MongoDB-specific types to plain Python types so the dict is
    safe to store in LangGraph state and serialise as JSON later.

    Handles:
    - ``datetime``        → ISO-8601 string
    - ``Decimal128``      → float
    - ``ObjectId``        → str  (should not appear after ``_id: 0``, but just in case)
    """
    from datetime import datetime

    result: dict[str, Any] = {}
    for key, value in order.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif hasattr(value, "to_decimal"):      # bson.Decimal128
            result[key] = float(value.to_decimal())
        elif hasattr(value, "__str__") and type(value).__name__ in ("ObjectId", "Decimal128"):
            result[key] = str(value)
        else:
            result[key] = value
    return result


if __name__ == "__main__":
    res = get_order_details("ORD-2001")
    print(res)
