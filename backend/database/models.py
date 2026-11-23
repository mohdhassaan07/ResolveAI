"""
MongoDB collection definitions and JSON-schema validators for resolve_AI.

Collections
-----------
customers       – Customer ID, name, email, account age
orders          – Order ID, customer ID, product, amount, delivery date, status
refunds         – Refund ID, order ID, amount, reason, status
refund_policies – Refund conditions, time limits, exceptions
audit_logs      – Tool calls, decisions, timestamps, outcomes
"""

from pymongo import ASCENDING, IndexModel
from pymongo.collection import Collection
from pymongo.errors import CollectionInvalid

from .connection import get_db


# ---------------------------------------------------------------------------
# JSON Schema validators
# ---------------------------------------------------------------------------

CUSTOMERS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["customer_id", "name", "email", "account_age_days", "total_refunds"],
        "properties": {
            "customer_id": {
                "bsonType": "string",
                "description": "Unique customer identifier (required)",
            },
            "name": {
                "bsonType": "string",
                "description": "Full name of the customer (required)",
            },
            "email": {
                "bsonType": "string",
                "pattern": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$",
                "description": "Customer e-mail address (required, valid format)",
            },
            "account_age_days": {
                "bsonType": "int",
                "minimum": 0,
                "description": "Age of account in days since registration (required)",
            },
            "created_at": {
                "bsonType": "date",
                "description": "UTC timestamp when the document was created",
            },
            "total_refunds": {
                "bsonType": "int",
                "minimum": 0,
                "description": "Total refunds of the customer (required)",
            },
        },
    }
}

ORDERS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["order_id", "customer_id", "product", "amount", "delivery_date", "status"],
        "properties": {
            "order_id": {
                "bsonType": "string",
                "description": "Unique order identifier (required)",
            },
            "customer_id": {
                "bsonType": "string",
                "description": "Reference to customers.customer_id (required)",
            },
            "product": {
                "bsonType": "string",
                "description": "Product name or SKU (required)",
            },
            "amount": {
                "bsonType": ["int", "double", "decimal"],
                "minimum": 0,
                "description": "Order total in base currency (required)",
            },
            "delivery_date": {
                "bsonType": "date",
                "description": "Expected or actual delivery date (required)",
            },
            "status": {
                "bsonType": "string",
                "enum": ["pending", "processing", "shipped", "delivered", "cancelled"],
                "description": "Current order status (required)",
            },
            "created_at": {"bsonType": "date"},
        },
    }
}

REFUNDS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["refund_id", "order_id", "amount", "reason", "status"],
        "properties": {
            "refund_id": {
                "bsonType": "string",
                "description": "Unique refund identifier (required)",
            },
            "order_id": {
                "bsonType": "string",
                "description": "Reference to orders.order_id (required)",
            },
            "amount": {
                "bsonType": ["int", "double", "decimal"],
                "minimum": 0,
                "description": "Refund amount in base currency (required)",
            },
            "reason": {
                "bsonType": "string",
                "description": "Reason provided for the refund (required)",
            },
            "status": {
                "bsonType": "string",
                "enum": ["requested", "under_review", "approved", "rejected", "processed"],
                "description": "Current refund status (required)",
            },
            "created_at": {"bsonType": "date"},
        },
    }
}

REFUND_POLICIES_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["policy_id", "conditions", "time_limit_days"],
        "properties": {
            "policy_id": {
                "bsonType": "string",
                "description": "Unique policy identifier (required)",
            },
            "conditions": {
                "bsonType": "array",
                "items": {"bsonType": "string"},
                "description": "List of refund eligibility conditions (required)",
            },
            "time_limit_days": {
                "bsonType": "int",
                "minimum": 0,
                "description": "Max days after purchase to request a refund (required)",
            },
            "exceptions": {
                "bsonType": "array",
                "items": {"bsonType": "string"},
                "description": "Items or scenarios exempt from this policy",
            },
            "is_active": {
                "bsonType": "bool",
                "description": "Whether this policy is currently active",
            },
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}

AUDIT_LOGS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["log_id", "case_id", "tool_call", "decision", "timestamp", "outcome"],
        "properties": {
            "log_id": {
                "bsonType": "string",
                "description": "Unique audit log identifier (required)",
            },
            "case_id": {
                "bsonType": "string",
                "description": "Reference to cases.case_id (required)",
            },
            "tool_call": {
                "bsonType": "object",
                "description": "Details of the tool/function that was invoked (required)",
                "properties": {
                    "name": {"bsonType": "string"},
                    "arguments": {"bsonType": "object"},
                },
            },
            "decision": {
                "bsonType": "string",
                "description": "Agent decision or action taken (required)",
            },
            "timestamp": {
                "bsonType": "date",
                "description": "UTC timestamp of the event (required)",
            },
            "outcome": {
                "bsonType": "string",
                "enum": ["success", "failure", "partial", "pending"],
                "description": "Result of the tool call / decision (required)",
            },
            "session_id": {
                "bsonType": "string",
                "description": "Optional agent session identifier",
            },
            "metadata": {
                "bsonType": "object",
                "description": "Any additional contextual data",
            },
        },
    }
}


CASES_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["case_id", "customer_id", "order_id", "request", "status"],
        "properties": {
            "case_id": {
                "bsonType": "string",
                "description": "Unique case identifier (required)",
            },
            "customer_id": {
                "bsonType": "string",
                "description": "Reference to customers.customer_id (required)",
            },
            "order_id": {
                "bsonType": "string",
                "description": "Reference to orders.order_id (required)",
            },
            "request": {
                "bsonType": "object",
                "description": "Customer's refund request details (required)",
                "properties": {
                    "reason": {"bsonType": "string"},
                    "description": {"bsonType": "string"},
                    "amount_requested": {"bsonType": ["double", "decimal"]},
                },
            },
            "status": {
                "bsonType": "string",
                "enum": [
                    "investigating",
                    "pending",
                    "awaiting_customer",
                    "awaiting_human_approval"
                    "approved",
                    "rejected",
                    "executed",
                    "closed",
                    "failed"
                ],
                "description": "Current case status (required)",
            },
            "investigation": {
                "bsonType": "object",
                "description": "Evidence collected by agents during investigation",
                "properties": {
                    "order_details": {"bsonType": "object"},
                    "refund_history": {"bsonType": "array", "items": {"bsonType": "object"}},
                    "policy_applied": {"bsonType": "string"},
                    "notes": {"bsonType": "string"},
                    "investigated_at": {"bsonType": "date"},
                },
            },
            "risk_assessment": {
                "bsonType": "object",
                "description": "Fraud and risk information assessed by agents",
                "properties": {
                    "risk_score": {"bsonType": ["double", "int"]},
                    "risk_level": {
                        "bsonType": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                    "flags": {"bsonType": "array", "items": {"bsonType": "string"}},
                    "assessed_at": {"bsonType": "date"},
                },
            },
            "decision": {
                "bsonType": "object",
                "description": "Agent's recommendation on the case",
                "properties": {
                    "recommendation": {
                        "bsonType": "string",
                        "enum": ["approve", "reject", "escalate"],
                    },
                    "amount_approved": {"bsonType": ["double", "decimal"]},
                    "reasoning": {"bsonType": "string"},
                    "decided_at": {"bsonType": "date"},
                    "decided_by": {"bsonType": "string"},
                },
            },
            "human_review": {
                "bsonType": "object",
                "description": "Human approval or rejection details",
                "properties": {
                    "reviewed_by": {"bsonType": "string"},
                    "action": {
                        "bsonType": "string",
                        "enum": ["approved", "rejected", "overridden"],
                    },
                    "notes": {"bsonType": "string"},
                    "reviewed_at": {"bsonType": "date"},
                },
            },
            "execution": {
                "bsonType": "object",
                "description": "Refund execution details after approval",
                "properties": {
                    "refund_id": {"bsonType": "string"},
                    "amount_refunded": {"bsonType": ["double", "decimal"]},
                    "method": {"bsonType": "string"},
                    "executed_at": {"bsonType": "date"},
                    "transaction_ref": {"bsonType": "string"},
                },
            },
            "created_at": {
                "bsonType": "date",
                "description": "UTC timestamp when the case was created",
            },
        },
    }
}


# ---------------------------------------------------------------------------
# Collection factory
# ---------------------------------------------------------------------------

def _create_collection(db, name: str, validator: dict) -> Collection:
    """Create a collection with schema validation; update validator if it already exists."""
    try:
        db.create_collection(
            name, validator={"$jsonSchema": validator["$jsonSchema"]})
        print(f"[models] Created collection: {name}")
    except CollectionInvalid:
        db.command("collMod", name, validator={
                   "$jsonSchema": validator["$jsonSchema"]})
        print(f"[models] Collection already exists, validator updated: {name}")
    return db[name]


# ---------------------------------------------------------------------------
# Index definitions
# ---------------------------------------------------------------------------

def _apply_indexes(db) -> None:
    db["customers"].create_indexes([
        IndexModel([("customer_id", ASCENDING)],
                   unique=True, name="idx_customer_id"),
        IndexModel([("email", ASCENDING)], unique=True, name="idx_email"),
    ])

    db["orders"].create_indexes([
        IndexModel([("order_id", ASCENDING)],
                   unique=True, name="idx_order_id"),
        IndexModel([("customer_id", ASCENDING)],
                   name="idx_orders_customer_id"),
        IndexModel([("status", ASCENDING)], name="idx_orders_status"),
    ])

    db["refunds"].create_indexes([
        IndexModel([("refund_id", ASCENDING)],
                   unique=True, name="idx_refund_id"),
        IndexModel([("order_id", ASCENDING)], name="idx_refunds_order_id"),
        IndexModel([("status", ASCENDING)], name="idx_refunds_status"),
    ])

    db["refund_policies"].create_indexes([
        IndexModel([("policy_id", ASCENDING)],
                   unique=True, name="idx_policy_id"),
        IndexModel([("is_active", ASCENDING)], name="idx_policy_active"),
    ])

    db["audit_logs"].create_indexes([
        IndexModel([("log_id", ASCENDING)], unique=True, name="idx_log_id"),
        IndexModel([("timestamp", ASCENDING)], name="idx_log_timestamp"),
        IndexModel([("outcome", ASCENDING)], name="idx_log_outcome"),
        IndexModel([("session_id", ASCENDING)], name="idx_log_session"),
        IndexModel([("case_id", ASCENDING)], name="idx_log_case_id"),
    ])

    db["cases"].create_indexes([
        IndexModel([("case_id", ASCENDING)], unique=True, name="idx_case_id"),
        IndexModel([("customer_id", ASCENDING)], name="idx_cases_customer_id"),
        IndexModel([("order_id", ASCENDING)], name="idx_cases_order_id"),
        IndexModel([("status", ASCENDING)], name="idx_cases_status"),
        IndexModel([("created_at", ASCENDING)], name="idx_cases_created_at"),
    ])

    print("[models] All indexes applied.")


# ---------------------------------------------------------------------------
# Public initialisation entry-point
# ---------------------------------------------------------------------------

def init_collections(db_name: str = "resolve_ai") -> dict[str, Collection]:
    """
    Create (or validate) all collections and their indexes.
    Call once at application startup.

    Returns a dict mapping collection name → Collection object.
    """
    db = get_db(db_name)

    customers = _create_collection(db, "customers",       CUSTOMERS_SCHEMA)
    orders = _create_collection(db, "orders",          ORDERS_SCHEMA)
    refunds = _create_collection(db, "refunds",         REFUNDS_SCHEMA)
    refund_policies = _create_collection(
        db, "refund_policies", REFUND_POLICIES_SCHEMA)
    audit_logs = _create_collection(db, "audit_logs",      AUDIT_LOGS_SCHEMA)
    cases = _create_collection(db, "cases",           CASES_SCHEMA)

    _apply_indexes(db)

    return {
        "customers":       customers,
        "orders":          orders,
        "refunds":         refunds,
        "refund_policies": refund_policies,
        "audit_logs":      audit_logs,
        "cases":           cases,
    }


# ---------------------------------------------------------------------------
# Convenience accessors
# ---------------------------------------------------------------------------

def get_customers_col(db_name: str = "resolve_ai") -> Collection:
    return get_db(db_name)["customers"]


def get_orders_col(db_name: str = "resolve_ai") -> Collection:
    return get_db(db_name)["orders"]


def get_refunds_col(db_name: str = "resolve_ai") -> Collection:
    return get_db(db_name)["refunds"]


def get_refund_policies_col(db_name: str = "resolve_ai") -> Collection:
    return get_db(db_name)["refund_policies"]


def get_audit_logs_col(db_name: str = "resolve_ai") -> Collection:
    return get_db(db_name)["audit_logs"]


def get_cases_col(db_name: str = "resolve_ai") -> Collection:
    return get_db(db_name)["cases"]
