#!/usr/bin/env python3
"""
Script to find and delete old views referencing icecat_specifications_grouped
Run this in Odoo shell or via odoo-bin shell
"""

# Find all views that contain the old field reference
views = env['ir.ui.view'].search([])
problematic_views = []

for view in views:
    if view.arch_db and 'icecat_specifications_grouped' in view.arch_db:
        problematic_views.append(view)
        print(f"Found view: {view.name} (ID: {view.id})")
        print(f"  Model: {view.model}")
        print(f"  XML ID: {view.xml_id}")
        print(f"  Module: {view.key.split('.')[0] if view.key else 'N/A'}")
        print()

print(f"\nTotal problematic views found: {len(problematic_views)}")

# Ask for confirmation before deleting
if problematic_views:
    print("\nTo delete these views, run:")
    print("for view in problematic_views:")
    print("    view.unlink()")
