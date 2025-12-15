# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    icecat_username = fields.Char(
        string='Icecat Username',
        config_parameter='product_content_verrijking.username',
        help='Your Icecat account username'
    )
    icecat_password = fields.Char(
        string='Icecat Password',
        config_parameter='product_content_verrijking.password',
        help='Your Icecat account password'
    )
    icecat_api_url = fields.Char(
        string='Icecat API URL',
        config_parameter='product_content_verrijking.api_url',
        default='https://live.icecat.biz/api',
        help='Icecat API base URL'
    )
    icecat_catalog_type = fields.Selection([
        ('open', 'Icecat Open Catalog'),
        ('full', 'Icecat Full Catalog'),
    ], string='Catalog Type',
        config_parameter='product_content_verrijking.catalog_type',
        default='open',
        help='Choose between Open (free) or Full (paid) catalog access'
    )
    icecat_new_product_batch_size = fields.Integer(
        string='New Products Batch Size',
        config_parameter='product_content_verrijking.new_product_batch_size',
        default=10,
        help='Number of products to sync per batch for new products (runs during day)'
    )
    icecat_update_batch_size = fields.Integer(
        string='Update Batch Size',
        config_parameter='product_content_verrijking.update_batch_size',
        default=100,
        help='Number of products to update per batch (runs at night)'
    )
    icecat_auto_sync_enabled = fields.Boolean(
        string='Enable Auto Sync',
        config_parameter='product_content_verrijking.auto_sync_enabled',
        help='Automatically sync products based on scheduled actions'
    )
    icecat_sync_description = fields.Boolean(
        string='Sync Description',
        config_parameter='product_content_verrijking.sync_description',
        help='Update product description from Icecat'
    )
    icecat_sync_images = fields.Boolean(
        string='Sync Images',
        config_parameter='product_content_verrijking.sync_images',
        help='Download and set product images from Icecat'
    )
    icecat_sync_specifications = fields.Boolean(
        string='Sync Specifications to Description',
        config_parameter='product_content_verrijking.sync_specifications',
        help='Add product specifications as HTML table in description'
    )
    icecat_sync_attributes = fields.Boolean(
        string='Sync Specifications as Attributes',
        config_parameter='product_content_verrijking.sync_attributes',
        help='Create Odoo product attributes from Icecat specifications (can create many attributes!)'
    )
    
    # Cron Job Settings
    icecat_cron_new_products_active = fields.Boolean(
        string='Enable New Products Sync',
        help='Enable automatic syncing of new products'
    )
    icecat_cron_new_products_interval = fields.Integer(
        string='New Products Interval',
        default=1,
        help='How often to sync new products'
    )
    icecat_cron_new_products_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
    ], string='Interval Type',
        default='hours',
        help='Interval type for new products sync'
    )
    
    icecat_cron_update_products_active = fields.Boolean(
        string='Enable Products Update',
        help='Enable automatic updating of existing products'
    )
    icecat_cron_update_products_interval = fields.Integer(
        string='Update Products Interval',
        default=1,
        help='How often to update existing products'
    )
    icecat_cron_update_products_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
    ], string='Update Interval Type',
        default='days',
        help='Interval type for products update'
    )
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        
        # Get cron records
        cron_new = self.env.ref('product_content_verrijking.ir_cron_sync_new_products', raise_if_not_found=False)
        cron_update = self.env.ref('product_content_verrijking.ir_cron_update_products', raise_if_not_found=False)
        
        if cron_new:
            res.update({
                'icecat_cron_new_products_active': cron_new.active,
                'icecat_cron_new_products_interval': cron_new.interval_number,
                'icecat_cron_new_products_interval_type': cron_new.interval_type,
            })
        
        if cron_update:
            res.update({
                'icecat_cron_update_products_active': cron_update.active,
                'icecat_cron_update_products_interval': cron_update.interval_number,
                'icecat_cron_update_products_interval_type': cron_update.interval_type,
            })
        
        return res
    
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        
        # Update cron records
        cron_new = self.env.ref('product_content_verrijking.ir_cron_sync_new_products', raise_if_not_found=False)
        cron_update = self.env.ref('product_content_verrijking.ir_cron_update_products', raise_if_not_found=False)
        
        if cron_new:
            cron_new.write({
                'active': self.icecat_cron_new_products_active,
                'interval_number': self.icecat_cron_new_products_interval,
                'interval_type': self.icecat_cron_new_products_interval_type,
            })
        
        if cron_update:
            cron_update.write({
                'active': self.icecat_cron_update_products_active,
                'interval_number': self.icecat_cron_update_products_interval,
                'interval_type': self.icecat_cron_update_products_interval_type,
            })

