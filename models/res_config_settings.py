# -*- coding: utf-8 -*-

from odoo import fields, models


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
