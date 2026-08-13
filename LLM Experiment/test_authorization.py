"""
test_authorization.py - Verification script for structural cross-account authorization guardrails in orders_store.py.
"""

import sys
from orders_store import get_order


def run_tests():
    print("Running Structural Authorization Guardrail Tests...")
    print("=" * 60)

    passed = 0
    total = 0

    # Test 1: Cross-account access (u001 requesting u002's order ord_3005)
    total += 1
    u001_id = "u001"
    u002_order_id = "ord_3005"  # Belongs to u002 in DATA-orders.json
    res_cross = get_order(u001_id, u002_order_id)
    if "error" in res_cross and res_cross.get("error") == f"Order '{u002_order_id}' not found":
        print(f"[PASS] Case 1: Cross-Account Access Blocked ({u001_id} requesting {u002_order_id})")
        print(f"       Returned: {res_cross}")
        passed += 1
    else:
        print(f"[FAIL] Case 1: Cross-Account Access Allowed! Got: {res_cross}")

    # Test 2: Non-existent order_id for valid user
    total += 1
    non_existent_order = "ord_99999"
    res_non_existent_order = get_order(u001_id, non_existent_order)
    if "error" in res_non_existent_order and res_non_existent_order.get("error") == f"Order '{non_existent_order}' not found":
        print(f"[PASS] Case 2: Non-existent Order Handled ({u001_id} requesting {non_existent_order})")
        print(f"       Returned: {res_non_existent_order}")
        passed += 1
    else:
        print(f"[FAIL] Case 2: Non-existent order unexpected response: {res_non_existent_order}")

    # Test 3: Non-existent user_id
    total += 1
    non_existent_user = "u9999"
    valid_order_id = "ord_3001"
    res_non_existent_user = get_order(non_existent_user, valid_order_id)
    if "error" in res_non_existent_user and res_non_existent_user.get("error") == f"Order '{valid_order_id}' not found":
        print(f"[PASS] Case 3: Non-existent User Handled ({non_existent_user} requesting {valid_order_id})")
        print(f"       Returned: {res_non_existent_user}")
        passed += 1
    else:
        print(f"[FAIL] Case 3: Non-existent user unexpected response: {res_non_existent_user}")

    # Test 4: Positive control - Valid user accessing their own order
    total += 1
    u001_order_id = "ord_3001"
    res_valid = get_order(u001_id, u001_order_id)
    if "order_id" in res_valid and res_valid.get("order_id") == u001_order_id and res_valid.get("user_id") == u001_id:
        print(f"[PASS] Case 4: Authorized Access Succeeded ({u001_id} requesting {u001_order_id})")
        print(f"       Returned: Order ID '{res_valid.get('order_id')}', Merchant: '{res_valid.get('merchant')}'")
        passed += 1
    else:
        print(f"[FAIL] Case 4: Authorized access failed! Got: {res_valid}")

    print("=" * 60)
    print(f"SUMMARY: {passed}/{total} authorization tests passed.")

    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
