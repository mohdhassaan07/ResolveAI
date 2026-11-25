# isort: skip_file
# ruff: noqa: E402
"""
customer_tools.py
-----------------
MongoDB helper + LangGraph node for customer history lookup.

Public surface
--------------
get_customer_history(customer_id)  – low-level query, returns dict or None
customer_history(state)            – LangGraph node; stores result in
                                     state["customer_history"]

Data fetched
------------
From `customers` collection:
  customer_id, name, email, account_age_days, total_refunds

From `refunds` collection (all refunds linked to this customer's orders):
  refund_id, order_id, amount, reason, status, created_at

Workflow routing
----------------
  customer found   → current_step = "policy_check"
  customer missing → case_status  = "customer_not_found" → handle_failure
"""
from __future__ import annotations

import os
import sys

# Ensure backend/ is on sys.path BEFORE any local package imports.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Any  # noqa: E402

from pymongo.errors import PyMongoError  # noqa: E402

from agents.state import RefundState  # noqa: E402
from database.models import (  # noqa: E402
    get_customers_col,
    get_orders_col,
    get_refunds_col,
)


# ---------------------------------------------------------------------------
# MongoDB helper
# ---------------------------------------------------------------------------

def get_customer_history(customer_id: str) -> dict[str, Any] | None:
    """
    Fetch a customer's profile and their full refund history from MongoDB.

    Parameters
    ----------
    customer_id:
        Unique customer identifier (e.g. ``"CUST001"``).

    Returns
    -------
    dict
        Combined customer profile + refund history::

            {
                "customer_id":      str,
                "name":             str,
                "email":            str,
                "account_age_days": int,
                "total_refunds":    int,
                "refund_history":   [ { refund doc }, ... ]   # may be []
            }

    None
        When no customer matches *customer_id*, or a DB error occurs.
    """
    try:
        customers_col = get_customers_col()
        refunds_col = get_refunds_col()
        orders_col = get_orders_col()

        # 1. Fetch the customer profile
        customer = customers_col.find_one(
            {"customer_id": customer_id},
            {"_id": 0}
        )
        if customer is None:
            return None

        # 2. Find all order_ids belonging to this customer
        order_ids: list[str] = [
            doc["order_id"]
            for doc in orders_col.find(
                {"customer_id": customer_id},
                {"_id": 0, "order_id": 1}
            )
        ]

        # 3. Fetch all refunds linked to those orders
        refund_history: list[dict] = []
        if order_ids:
            refund_history = list(
                refunds_col.find(
                    {"order_id": {"$in": order_ids}},
                    {"_id": 0}
                )
            )

        return {
            **customer,
            "refund_history": refund_history,
        }

    except PyMongoError as exc:
        import sys as _sys
        print(
            f"[customer_tools] MongoDB error for customer_id={customer_id!r}: {exc}",
            file=_sys.stderr,
        )
        return None


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def customer_history(state: RefundState) -> dict:
    """
    LangGraph node: fetch customer profile + refund history, store in state.

    Reads
    -----
    state["customer_id"]  – promoted by validate_request

    Writes (partial state dict merged by LangGraph into RefundState)
    -----------------------------------------------------------------------
    customer_history  → dict   (found)   | None  (not found)
    case_status       → "in_progress"    | "customer_not_found"
    current_step      → "policy_check"   | "customer_history"
    errors            → appended on failure
    """

    customer_id: str = (state.get("customer_id") or "").strip()
    errors: list[str] = list(state.get("errors") or [])

    # ------------------------------------------------------------------ #
    # Guard: customer_id must be present
    # ------------------------------------------------------------------ #
    if not customer_id:
        errors.append(
            "customer_history: 'customer_id' is missing from state. "
            "Make sure validate_request ran successfully before this node."
        )
        return {
            "customer_history": None,
            "case_status": "customer_not_found",
            "current_step": "customer_history",
            "errors": errors,
        }

    # ------------------------------------------------------------------ #
    # Fetch from MongoDB
    # ------------------------------------------------------------------ #
    history: dict[str, Any] | None = get_customer_history(customer_id)

    # ------------------------------------------------------------------ #
    # Customer NOT found (or DB error)
    # ------------------------------------------------------------------ #
    if history is None:
        errors.append(
            f"Customer '{customer_id}' was not found in the system. "
            "Cannot proceed with the refund without a valid customer record."
        )
        return {
            "customer_history": None,
            "case_status": "customer_not_found",
            "current_step": "customer_history",
            "errors": errors,
        }

    # ------------------------------------------------------------------ #
    # Serialize datetime / Decimal128 / ObjectId before storing in state
    # ------------------------------------------------------------------ #
    history = _serialize(history)

    return {
        "customer_history": history,   # → state["customer_history"]
        "case_status": "in_progress",
        "current_step": "policy_check",
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Internal serialisation helper
# ---------------------------------------------------------------------------

def _serialize(data: Any) -> Any:
    """
    Recursively convert MongoDB-specific types to plain Python types so the
    result is safe to store in LangGraph state and serialise as JSON later.

    Handles
    -------
    - ``datetime``   → ISO-8601 string
    - ``Decimal128`` → float
    - ``ObjectId``   → str
    - ``dict``       → each value converted recursively
    - ``list``       → each element converted recursively
    """
    from datetime import datetime

    if isinstance(data, datetime):
        return data.isoformat()
    if hasattr(data, "to_decimal"):                         # bson.Decimal128
        return float(data.to_decimal())
    if type(data).__name__ in ("ObjectId", "Decimal128"):   # fallback str
        return str(data)
    if isinstance(data, dict):
        return {k: _serialize(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_serialize(item) for item in data]
    return data


# ---------------------------------------------------------------------------
# Quick smoke-test (run directly: uv run .\backend\tools\customer_tools.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    result = get_customer_history("CUST001")
    print(json.dumps(result, indent=2, default=str))
