# -*- coding: utf-8 -*-

from collections import defaultdict
from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale


class IcecatWebsiteSale(WebsiteSale):
    
    def _prepare_product_values(self, product, category, search, **kwargs):
        """Override to add grouped attributes for accordion display"""
        values = super()._prepare_product_values(product, category, search, **kwargs)
        
        # Group attributes by category for accordion display
        if product.attribute_line_ids:
            attr_groups = defaultdict(list)
            for line in product.attribute_line_ids:
                attr_name = line.attribute_id.name
                # Extract group and name from "Group: Name" format
                if ':' in attr_name:
                    parts = attr_name.split(':', 1)
                    group = parts[0].strip()
                    name = parts[1].strip()
                else:
                    group = 'General'
                    name = attr_name
                
                value = line.value_ids[0].name if line.value_ids else ''
                attr_groups[group].append((name, value))
            
            # Convert to sorted list for template
            values['attribute_groups'] = sorted(attr_groups.items())
        else:
            values['attribute_groups'] = []
        
        return values
