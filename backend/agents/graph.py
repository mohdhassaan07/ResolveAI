from langgraph.graph import StateGraph, START, END

from agents.state import RefundState
from tools.validate import validate_request
from tools.order_tools import order_lookup
from tools.customer_tools import customer_history
from tools.failure_tools import handle_failure


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

def route_after_validate(state: RefundState) -> str:
    """After validate_request: stop on invalid input, else proceed."""
    if state.get("case_status") == "invalid_request":
        return "handle_failure"
    return "order_lookup"


def route_after_order_lookup(state: RefundState) -> str:
    """After order_lookup: stop if order missing, else proceed."""
    if state.get("case_status") == "order_not_found":
        return "handle_failure"
    return "customer_history"


def route_after_customer_history(state: RefundState) -> str:
    """After customer_history: stop if customer missing, else proceed."""
    if state.get("case_status") == "customer_not_found":
        return "handle_failure"
    return "policy_check"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

builder = StateGraph(RefundState)

# Register nodes
builder.add_node("validate_request", validate_request)
builder.add_node("order_lookup", order_lookup)
builder.add_node("customer_history", customer_history)
# builder.add_node("policy_check", policy_check)
# builder.add_node("fraud_check", fraud_check)
# builder.add_node("decision_maker", decision_maker)
# builder.add_node("human_review", human_review)
# builder.add_node("execute_refund", execute_refund)
# builder.add_node("finalize_case", finalize_case)
builder.add_node("handle_failure", handle_failure)
# Entry point
builder.add_edge(START, "validate_request")

# Conditional routing: validate → order_lookup OR handle_failure
builder.add_conditional_edges(
    "validate_request",
    route_after_validate,
    {"order_lookup": "order_lookup", "handle_failure": "handle_failure"},
)

# Conditional routing: order_lookup → customer_history OR handle_failure
builder.add_conditional_edges(
    "order_lookup",
    route_after_order_lookup,
    {"customer_history": "customer_history", "handle_failure": "handle_failure"},
)

# Conditional routing: customer_history → policy_check OR handle_failure
# builder.add_conditional_edges(
#     "customer_history",
#     route_after_customer_history,
#     {"policy_check": "policy_check", "handle_failure": "handle_failure"},
# )
builder.add_edge("customer_history", END)
# builder.add_edge("policy_check", "fraud_check")
# builder.add_edge("fraud_check", "decision_maker")

# Conditional decision routing
# builder.add_conditional_edges(
#     "decision_maker",
#     route_decision,
# )

# # Human approval routing
# builder.add_conditional_edges(
#     "human_review",
#     route_human_review,
# )

# # Finalization
# builder.add_edge("execute_refund", "finalize_case")
# builder.add_edge("finalize_case", END)

# Failure handling
builder.add_edge("handle_failure", END)

workflow = builder.compile()

res = workflow.invoke({
    "request": {
        "customer_id": "CUST-1001",
        "order_id":    "ORD-2001",
        "reason":      "I didn't like the quality of the product",
        "amount":      2499,
    }
})
print("current_step :", res.get("current_step"))
print("case_status  :", res.get("case_status"))
print("order_details:", res.get("order_details"))
print("cust_history :", res.get("customer_history"))
