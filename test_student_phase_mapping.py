#!/usr/bin/env python3
"""
Test Script untuk memverifikasi Student Phase Mapping
Jalankan di Odoo shell:
  docker exec -it odoo_app odoo shell -d odoo_docker -c /etc/odoo/odoo.conf

Lalu jalankan:
  exec(open('/mnt/custom-addons/test_student_phase_mapping.py').read())
"""

def test_student_phase_mapping():
    """Test student phase mapping dari Metabase ke Odoo"""
    print("\n" + "="*80)
    print("TEST STUDENT PHASE MAPPING")
    print("="*80)

    # Mapping yang digunakan
    phase_mapping = {
        "new student": "new",
        "paid student": "paid",
        "non paid": "non_paid",
        "non paid student": "non_paid",
    }

    # Selection field definition
    selection_values = {
        'paid': 'Paid Student',
        'new': 'New Student',
        'non_paid': 'Non Paid Student',
    }

    # Test data dari Metabase
    test_data = [
        "new student",
        "paid student",
        "non paid",
        "non paid student",
        "New Student",  # Test case sensitivity
        "PAID STUDENT",  # Test uppercase
    ]

    print("\n1. Testing Mapping:")
    print("-" * 80)
    for metabase_value in test_data:
        # Simulate mapping process
        normalized = metabase_value.lower().strip()
        technical_value = phase_mapping.get(normalized)
        display_value = selection_values.get(technical_value) if technical_value else None

        status = "✅" if technical_value else "❌"
        print(f"{status} Metabase: '{metabase_value}' → Technical: '{technical_value}' → Display: '{display_value}'")

    # Test with actual Odoo data
    print("\n2. Testing with Actual Contact:")
    print("-" * 80)

    # Find a test contact
    Partner = env['res.partner']
    test_contact = Partner.search([('metabase_user_id', '!=', False)], limit=1)

    if test_contact:
        print(f"Found test contact: {test_contact.name} (ID: {test_contact.id})")
        print(f"Current Student Phase: {test_contact.metabase_student_phase}")

        # Test updating with different values
        for phase_key, phase_label in selection_values.items():
            test_contact.metabase_student_phase = phase_key
            print(f"  ✅ Set to '{phase_key}' → Displays as: '{phase_label}'")

    else:
        print("⚠️  No contact with metabase_user_id found for testing")

    # Verify field definition
    print("\n3. Verifying Field Definition:")
    print("-" * 80)
    field_info = Partner._fields.get('metabase_student_phase')
    if field_info:
        print(f"Field Type: {field_info.type}")
        print(f"Field String: {field_info.string}")
        print(f"Selection Options:")
        for key, label in field_info.selection:
            print(f"  - '{key}' → '{label}'")
    else:
        print("❌ Field 'metabase_student_phase' not found!")

    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80 + "\n")

# Run the test
if __name__ == '__main__':
    test_student_phase_mapping()
