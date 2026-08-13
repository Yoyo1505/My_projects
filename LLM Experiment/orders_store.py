"""
orders_store.py - Loads and queries DATA-orders.json for the SplitWave Support Agent.
"""

import json
import os
from typing import Dict, List, Optional, Any

_ORDERS_CACHE: Optional[Dict[str, Any]] = None


def load_orders(path: str = "DATA-orders.json") -> Dict[str, Any]:
    """Loads DATA-orders.json (caching in module state)."""
    global _ORDERS_CACHE
    if _ORDERS_CACHE is not None:
        return _ORDERS_CACHE

    target_path = path
    if not os.path.isabs(target_path) and not os.path.exists(target_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(base_dir, path)
        if os.path.exists(alt_path):
            target_path = alt_path

    with open(target_path, "r", encoding="utf-8") as f:
        _ORDERS_CACHE = json.load(f)

    return _ORDERS_CACHE


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user profile by user_id."""
    data = load_orders()
    for user in data.get("users", []):
        if user.get("user_id") == user_id:
            return user
    return None


def get_orders_for_user(user_id: str) -> List[Dict[str, Any]]:
    """Get all orders belonging to user_id."""
    data = load_orders()
    return [order for order in data.get("orders", []) if order.get("user_id") == user_id]


def get_order(user_id: str, order_id: str) -> Dict[str, Any]:
    """
    CRITICAL GUARDRAIL: Get order details by user_id and order_id.
    If order_id exists but belongs to a different user_id, this MUST return the same
    not found error as a non-existent order.
    """
    data = load_orders()
    for order in data.get("orders", []):
        if order.get("order_id") == order_id:
            if order.get("user_id") == user_id:
                return order
            else:
                # Security guardrail: Order belongs to someone else
                return {"error": f"Order '{order_id}' not found"}
    return {"error": f"Order '{order_id}' not found"}


def get_next_payment(user_id: str, order_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the next upcoming or failed installment (soonest due_date with status in {upcoming, failed})
    across the user's orders, or within one order if order_id is given and owned by user_id.
    Uses 'today' from the JSON for date context.
    """
    if order_id:
        order = get_order(user_id, order_id)
        if "error" in order:
            return order
        candidate_orders = [order]
    else:
        candidate_orders = get_orders_for_user(user_id)

    candidates = []
    for order in candidate_orders:
        for inst in order.get("installments", []):
            if inst.get("status") in ("upcoming", "failed"):
                candidates.append({
                    "order_id": order.get("order_id"),
                    "merchant": order.get("merchant"),
                    "installment": inst.get("installment"),
                    "amount": inst.get("amount"),
                    "due_date": inst.get("due_date"),
                    "status": inst.get("status"),
                    "paid_date": inst.get("paid_date"),
                    "order_status": order.get("status"),
                    "reschedules_used": order.get("reschedules_used", 0),
                    "refund": order.get("refund"),
                })

    if not candidates:
        return {"message": f"No upcoming or failed payments found for user {user_id}"}

    candidates.sort(key=lambda x: x["due_date"])
    return candidates[0]
