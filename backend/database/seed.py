# isort: skip_file
import sys
import os

# Must come before any local imports — patches sys.path so `database`
# is resolvable when this script is run directly:
#   uv run .\backend\database\seed.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.connection import get_db  # noqa: E402

db = get_db()

customers = [
    {
        "customer_id": "CUST001",
        "name": "Rahul",
        "email": "rahul@example.com",
        "account_age_days": 365,
        "total_refunds": 0
    },
    {
        "customer_id": "CUST002",
        "name": "hassaan",
        "email": "hassaan@example.com",
        "account_age_days": 200,
        "total_refunds": 0
    },
]

result = db.customers.insert_many(customers)

print("Inserted IDs:", result.inserted_ids)
