# isort: skip_file
# ruff: noqa: E402
"""
failure_tools.py
----------------
LangGraph node: handle_failure

Centralised failure handler for the resolve_AI refund workflow.
Called whenever any upstream node sets a non-"in_progress" case_status.

Failure statuses handled
------------------------
  invalid_request     – validate_request: missing / bad fields
  order_not_found     – order_lookup: order doesn't exist in DB
  customer_not_found  – customer_history: customer doesn't exist in DB
  (any other value)   – unexpected / unclassified failure

What the node does
------------------
1. Reads state["case_status"] and state["errors"] to understand what failed.
2. Builds a structured failure_summary dict.
3. Sets case_status → "failed" (terminal).
4. Sets current_step → "handle_failure".
5. Returns the partial state — LangGraph merges it, then the edge to END
   closes the workflow.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.state import RefundState  # noqa: E402


# ---------------------------------------------------------------------------
# Human-readable labels for each failure status
# ---------------------------------------------------------------------------

_FAILURE_MESSAGES: dict[str, str] = {
    "invalid_request":    "The refund request is missing required fields or contains invalid values.",
    "order_not_found":    "The order ID provided does not match any record in our system.",
    "customer_not_found": "The customer ID provided does not match any record in our system.",
}

_DEFAULT_FAILURE_MESSAGE = "An unexpected error occurred while processing the refund request."


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def handle_failure(state: RefundState) -> dict:
    """
    LangGraph node: centralised failure handler.

    Reads
    -----
    state["case_status"]   – the failure type set by the failing node
    state["errors"]        – list of error messages accumulated so far
    state["case_id"]       – used for logging (may be absent on early failure)
    state["customer_id"]   – for context in the summary
    state["order_id"]      – for context in the summary

    Writes (partial state merged by LangGraph)
    ------------------------------------------
    case_status      → "failed"
    current_step     → "handle_failure"
    refund_result    → structured failure summary dict
    """

    failed_status: str = state.get("case_status") or "unknown"
    errors: list[str] = list(state.get("errors") or [])
    case_id: str = state.get("case_id") or "N/A"
    customer_id: str = state.get("customer_id") or "N/A"
    order_id: str = state.get("order_id") or "N/A"

    # Resolve a user-facing reason from the known status codes
    reason: str = _FAILURE_MESSAGES.get(
        failed_status, _DEFAULT_FAILURE_MESSAGE)

    # Build a structured failure summary stored in state["refund_result"]
    # so that the caller / API layer can inspect exactly what went wrong.
    failure_summary: dict = {
        "outcome":      "failure",
        "failed_at":    failed_status,              # which stage failed
        "reason":       reason,                     # human-readable label
        "errors":       errors,                     # detailed error list
        "case_id":      case_id,
        "customer_id":  customer_id,
        "order_id":     order_id,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
    }

    # Print to stderr so failures are visible in server logs
    print(
        f"[handle_failure] case_id={case_id!r} "
        f"failed_at={failed_status!r} "
        f"errors={errors}",
        file=sys.stderr,
    )

    return {
        "case_status":   "failed",
        "current_step":  "handle_failure",
        "refund_result": failure_summary,
    }
