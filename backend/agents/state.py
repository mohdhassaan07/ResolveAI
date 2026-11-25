from typing import TypedDict, Optional, Any


class RefundState(TypedDict, total=False):

    # 1. Request information
    case_id: str
    customer_id: str
    order_id: str

    request: dict

    # 2. Investigation results
    order_details: Optional[dict]
    customer_history: Optional[dict]
    refund_policy: Optional[dict]

    investigation_evidence: list

    # 3. Fraud and risk assessment
    risk_score: Optional[float]
    risk_level: Optional[str]
    risk_factors: list

    # 4. Decision
    decision: Optional[str]
    decision_reason: Optional[str]
    approved_amount: Optional[float]

    # 5. Human review
    human_review_required: bool
    human_approval: Optional[bool]
    reviewer_id: Optional[str]
    reviewer_comments: Optional[str]

    # 6. Refund execution
    refund_result: Optional[dict]
    case_status: str

    # 7. Workflow control
    current_step: str
    retry_counts: dict
    errors: list

    # 8. Token usage and monitoring
    total_input_tokens: int
    total_output_tokens: int
