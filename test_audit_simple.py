"""
Simple test to verify audit description generation works correctly
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.utils.audit_descriptions import get_audit_description

# Test data - simulating different types of audit logs
test_logs = [
    {
        'id': 1,
        'entity_type': 'claim',
        'entity_id': 123,
        'action': 'APPROVE',
        'old_values': {'status': 'PENDING'},
        'new_values': {'status': 'APPROVED', 'final_amount': 5000.00},
        'performed_by_name': 'John Doe',
        'metadata': {'claim_number': '#123'}
    },
    {
        'id': 2,
        'entity_type': 'employee',
        'entity_id': 45,
        'action': 'CREATE',
        'old_values': {},
        'new_values': {'role': 'manager', 'name': 'Jane Smith'},
        'performed_by_name': 'Admin',
        'metadata': {'employee_name': 'Jane Smith'}
    },
    {
        'id': 3,
        'entity_type': 'auth',
        'entity_id': 10,
        'action': 'LOGIN',
        'old_values': {},
        'new_values': {},
        'performed_by_name': 'John Doe',
        'metadata': {}
    },
    {
        'id': 4,
        'entity_type': 'unit',
        'entity_id': 5,
        'action': 'CREATE',
        'old_values': {},
        'new_values': {'name': 'Finance Department'},
        'performed_by_name': 'Admin',
        'metadata': {'name': 'Finance Department'}
    },
    {
        'id': 5,
        'entity_type': 'category',
        'entity_id': 8,
        'action': 'UPDATE',
        'old_values': {'cap': 1000.00, 'name': 'Travel'},
        'new_values': {'cap': 1500.00, 'name': 'Travel'},
        'performed_by_name': 'Manager',
        'metadata': {'name': 'Travel'}
    }
]

print("Testing Audit Description Generation\n")
print("=" * 70)

for log in test_logs:
    description = get_audit_description(log)
    print(f"\nEntity Type: {log['entity_type']}")
    print(f"Action: {log['action']}")
    print(f"DESCRIPTION: {description}")
    print("-" * 70)

print("\nSUCCESS: All audit descriptions generated successfully!")
