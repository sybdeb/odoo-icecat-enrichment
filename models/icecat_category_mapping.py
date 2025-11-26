# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class IcecatCategoryMapping(models.Model):
    _name = 'icecat.category.mapping'
    _description = 'Icecat to Odoo Category Mapping'
    _rec_name = 'icecat_category'

    icecat_category = fields.Char(
        string='Icecat Category',
        required=True,
        help='Category name from Icecat'
    )
    odoo_category_id = fields.Many2one(
        'product.public.category',
        string='Website Category',
        help='Odoo website product category'
    )
    internal_category_id = fields.Many2one(
        'product.category',
        string='Internal Category',
        help='Odoo internal product category'
    )
    google_category_id = fields.Many2one(
        'product.google.category',
        string='Google Shopping Category',
        help='Google Shopping product category',
        ondelete='set null'
    )
    auto_publish = fields.Boolean(
        string='Auto Publish to Website',
        default=True,
        help='Automatically publish products to website when synced'
    )
    product_count = fields.Integer(
        string='Products',
        compute='_compute_product_count',
        help='Number of products with this Icecat category'
    )

    _sql_constraints = [
        ('icecat_category_unique', 'unique(icecat_category)', 
         'This Icecat category already has a mapping!'),
    ]

    @api.depends('icecat_category')
    def _compute_product_count(self):
        """Count products with this Icecat category"""
        for mapping in self:
            mapping.product_count = self.env['product.template'].search_count([
                ('icecat_category', '=', mapping.icecat_category)
            ])

    @api.model
    def get_mapping(self, icecat_category):
        """Get mapping for an Icecat category, create default if not exists"""
        if not icecat_category:
            return None
        
        mapping = self.search([('icecat_category', '=', icecat_category)], limit=1)
        
        if not mapping:
            # Create a basic mapping
            mapping = self.create({
                'icecat_category': icecat_category,
                'auto_publish': True,  # Auto-publish by default
            })
        
        return mapping

    @api.model
    def _create_category_hierarchy(self, category_path, model_name):
        """
        Create a category hierarchy from a path like 'Electronics > Computers > Monitors'
        Returns the deepest (leaf) category
        """
        if not category_path:
            return None
        
        # Split the path by ' > '
        parts = [part.strip() for part in category_path.split('>')]
        
        parent = None
        category_obj = self.env[model_name]
        
        for part in parts:
            # Search for existing category with this name and parent
            domain = [('name', '=', part)]
            if parent:
                domain.append(('parent_id', '=', parent.id))
            else:
                domain.append(('parent_id', '=', False))
            
            category = category_obj.search(domain, limit=1)
            
            if not category:
                # Create the category
                vals = {'name': part}
                if parent:
                    vals['parent_id'] = parent.id
                category = category_obj.create(vals)
            
            parent = category
        
        return parent  # Return the deepest category

    @api.model
    def apply_mapping(self, product, icecat_category):
        """Apply category mapping to a product"""
        mapping = self.get_mapping(icecat_category)
        
        if not mapping:
            return {}
        
        vals = {}
        
        # If Google category is set, create hierarchies automatically
        if mapping.google_category_id:
            google_cat_name = mapping.google_category_id.name
            
            # Create website category hierarchy if not manually set
            if not mapping.odoo_category_id:
                website_cat = self._create_category_hierarchy(google_cat_name, 'product.public.category')
                if website_cat:
                    mapping.write({'odoo_category_id': website_cat.id})
            
            # Create internal category hierarchy if not manually set
            if not mapping.internal_category_id:
                # For internal categories, we might want to prepend "All" as root
                internal_cat = self._create_category_hierarchy(google_cat_name, 'product.category')
                if internal_cat:
                    mapping.write({'internal_category_id': internal_cat.id})
        
        # Set website category
        if mapping.odoo_category_id:
            vals['public_categ_ids'] = [(4, mapping.odoo_category_id.id)]
        
        # Set internal category
        if mapping.internal_category_id:
            vals['categ_id'] = mapping.internal_category_id.id
        
        # Set Google category (only if the field exists on product.template)
        if mapping.google_category_id and hasattr(product, 'google_category_id'):
            vals['google_category_id'] = mapping.google_category_id.id
        
        # Set website published
        if mapping.auto_publish:
            vals['is_published'] = True
        
        return vals

    def action_apply_to_products(self):
        """Apply this mapping to all products with this Icecat category"""
        self.ensure_one()
        
        # Find all products with this Icecat category
        products = self.env['product.template'].search([
            ('icecat_category', '=', self.icecat_category)
        ])
        
        if not products:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Products'),
                    'message': _('No products found with this Icecat category.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Apply mapping to all products
        vals = self.apply_mapping(products[0], self.icecat_category)
        if vals:
            # Remove the single product specific update and apply to all
            products.write(vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Mapping applied to %d products.') % len(products),
                'type': 'success',
                'sticky': False,
            }
        }
