# isort: skip_file
# ruff: noqa: E402
"""
validate.py
-----------
LangGraph node: validate_request

Receives the initial refund request (from RefundState.request) and checks
that all required fields are present and well-formed.

Checks performed
----------------
1. customer_id  – must be a non-empty string
2. order_id     – must be a non-empty string
3. reason       – must be a non-empty string (refund reason)
4. amount       – must be a positive number

On failure the node sets:
  - case_status  → "invalid_request"
  - current_step → "validate_request"
  - errors       → list of human-readable messages (one per failing check)

On success it promotes the validated fields into the top-level state keys
(customer_id, order_id) and advances current_step to "order_lookup".
"""
from __future__ import annotations

import os
import sys
import uuid

# Ensure the backend/ directory is on sys.path so that sibling packages
# (agents, database, tools) are importable regardless of launch location.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Any  # noqa: E402

from agents.state import RefundState  # noqa: E402


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_non_empty_string(value: Any) -> bool:
    """Return True when *value* is a str with at least one non-whitespace char."""
    return isinstance(value, str) and bool(value.strip())


def _is_positive_number(value: Any) -> bool:
    """Return True when *value* is a finite, positive int or float."""
    if not isinstance(value, (int, float)):
        return False
    if isinstance(value, bool):          # bool subclasses int – reject it
        return False
    return value > 0


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def validate_request(state: RefundState) -> RefundState:
    """
    Validate the incoming refund request stored in ``state["request"]``.

    Returns a *partial* state dict that LangGraph merges into the full state.
    """

    request: dict = state.get("request") or {}
    errors: list[str] = list(state.get("errors") or [])

    # ------------------------------------------------------------------ #
    # 1. customer_id
    # ------------------------------------------------------------------ #
    customer_id: str = request.get("customer_id", "")
    if not _is_non_empty_string(customer_id):
        errors.append(
            "Missing or invalid 'customer_id'. "
            "Please provide a valid customer identifier."
        )

    # ------------------------------------------------------------------ #
    # 2. order_id
    # ------------------------------------------------------------------ #
    order_id: str = request.get("order_id", "")
    if not _is_non_empty_string(order_id):
        errors.append(
            "Missing or invalid 'order_id'. "
            "Please provide the order number you wish to refund."
        )

    # ------------------------------------------------------------------ #
    # 3. reason  (refund reason)
    # ------------------------------------------------------------------ #
    reason: str = request.get("reason", "")
    if not _is_non_empty_string(reason):
        errors.append(
            "Missing or invalid 'reason'. "
            "Please describe why you are requesting a refund."
        )

    # ------------------------------------------------------------------ #
    # 4. amount  (requested refund amount)
    # ------------------------------------------------------------------ #
    amount = request.get("amount")
    if not _is_positive_number(amount):
        errors.append(
            "Missing or invalid 'amount'. "
            "Please provide a positive numeric value for the refund amount."
        )

    # ------------------------------------------------------------------ #
    # Build the state update
    # ------------------------------------------------------------------ #
    if errors:
        # Workflow stops here – graph routes to handle_failure / END
        return {
            "case_status": "invalid_request",
            "current_step": "validate_request",
            "errors": errors,
            # Keep whatever valid fields were found so downstream can inspect
            "customer_id": customer_id.strip() if _is_non_empty_string(customer_id) else "",
            "order_id": order_id.strip() if _is_non_empty_string(order_id) else "",
        }

    # All checks passed → promote fields and advance the workflow
    case_id: str = state.get(
        "case_id") or f"CASE-{uuid.uuid4().hex[:8].upper()}"

    return {
        "case_id": case_id,
        "customer_id": customer_id.strip(),
        "order_id": order_id.strip(),
        "case_status": "in_progress",
        "current_step": "order_lookup",
        "errors": [],          # clear any stale errors from previous runs
    }
