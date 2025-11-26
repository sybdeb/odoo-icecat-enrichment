#!/usr/bin/env python3
"""
Cleanup script voor Icecat product attributes
Verwijdert alle [Icecat] prefixed attributes en hun koppelingen

Gebruik via Portainer console:
1. Ga naar Odoo container
2. Console > /bin/bash
3. cd /mnt/extra-addons/icecat_product_enrichment
4. python3 cleanup_icecat_attributes.py

Of direct via odoo shell:
odoo-bin shell -d <database_name> --no-http < cleanup_icecat_attributes.py
"""

import logging

_logger = logging.getLogger(__name__)

def cleanup_icecat_attributes(env):
    """
    Verwijdert alle Icecat-gerelateerde product attributes
    """
    _logger.info("Starting Icecat attributes cleanup...")
    
    # Find all attributes with [Icecat] prefix
    Attribute = env['product.attribute']
    icecat_attributes = Attribute.search([
        ('name', 'ilike', '[Icecat]%')
    ])
    
    if not icecat_attributes:
        _logger.info("No Icecat attributes found. Nothing to clean up.")
        return
    
    attribute_count = len(icecat_attributes)
    _logger.info(f"Found {attribute_count} Icecat attributes to remove")
    
    # Find all attribute lines linked to these attributes
    AttributeLine = env['product.template.attribute.line']
    icecat_lines = AttributeLine.search([
        ('attribute_id', 'in', icecat_attributes.ids)
    ])
    
    line_count = len(icecat_lines)
    _logger.info(f"Found {line_count} product attribute lines to remove")
    
    # Find all attribute values
    AttributeValue = env['product.attribute.value']
    icecat_values = AttributeValue.search([
        ('attribute_id', 'in', icecat_attributes.ids)
    ])
    
    value_count = len(icecat_values)
    _logger.info(f"Found {value_count} attribute values to remove")
    
    # Delete in correct order to avoid foreign key errors
    _logger.info("Step 1/3: Removing attribute lines from products...")
    icecat_lines.unlink()
    _logger.info(f"✓ Removed {line_count} attribute lines")
    
    _logger.info("Step 2/3: Removing attribute values...")
    icecat_values.unlink()
    _logger.info(f"✓ Removed {value_count} attribute values")
    
    _logger.info("Step 3/3: Removing attributes...")
    icecat_attributes.unlink()
    _logger.info(f"✓ Removed {attribute_count} attributes")
    
    env.cr.commit()
    
    _logger.info("=" * 60)
    _logger.info("Cleanup completed successfully!")
    _logger.info(f"Summary:")
    _logger.info(f"  - Attributes removed: {attribute_count}")
    _logger.info(f"  - Attribute values removed: {value_count}")
    _logger.info(f"  - Product attribute lines removed: {line_count}")
    _logger.info("=" * 60)
    
    print("\n" + "=" * 60)
    print("✓ Icecat attributes cleanup COMPLETED")
    print(f"  Removed {attribute_count} attributes")
    print(f"  Removed {value_count} attribute values")
    print(f"  Removed {line_count} product attribute lines")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    # When run via odoo shell, env is available
    try:
        cleanup_icecat_attributes(env)
    except NameError:
        print("ERROR: This script must be run via Odoo shell:")
        print("  odoo-bin shell -d <database_name> --no-http < cleanup_icecat_attributes.py")
        print("\nOr copy-paste the cleanup_icecat_attributes(env) call in the Odoo shell")
