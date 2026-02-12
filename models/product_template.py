# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    icecat_sync_status = fields.Selection([
        ('not_synced', 'Not Synced'),
        ('pending', 'Pending Sync'),
        ('synced', 'Synced'),
        ('error', 'Error'),
        ('no_data', 'No Data Available'),
    ], string='Icecat Sync Status',
        default='not_synced',
        help='Current synchronization status with Icecat'
    )
    icecat_last_sync = fields.Datetime(
        string='Last Icecat Sync',
        readonly=True,
        help='Last time this product was synced with Icecat'
    )
    icecat_product_id = fields.Char(
        string='Icecat Product ID',
        readonly=True,
        help='Icecat internal product identifier'
    )
    icecat_error_message = fields.Text(
        string='Icecat Error Message',
        readonly=True,
        help='Last error message from Icecat sync'
    )
    icecat_brand = fields.Char(
        string='Icecat Brand',
        readonly=True,
        help='Brand name from Icecat'
    )
    icecat_category = fields.Char(
        string='Icecat Category',
        readonly=True,
        help='Category from Icecat'
    )
    icecat_quality = fields.Selection([
        ('ICECAT', 'ICECAT'),
        ('SUPPLIED', 'SUPPLIED'),
    ], string='Icecat Quality',
        readonly=True,
        help='Data quality indicator from Icecat'
    )
    icecat_specifications_raw = fields.Json(
        string='Icecat Specifications Raw',
        readonly=True,
        help='Raw specifications data from Icecat, stored as JSON (source of truth)'
    )
    
    # TEMPORARY: Deprecated field to prevent crashes from old cached views
    # Will be removed after all views are updated
    icecat_specifications_grouped = fields.Html(
        string='Specifications (Deprecated)',
        compute='_compute_icecat_specifications_grouped_dummy',
        help='DEPRECATED - This field does nothing and will be removed'
    )
    
    icecat_attributes_count = fields.Integer(
        string='Attributes Count',
        compute='_compute_icecat_attributes_count',
        help='Number of Icecat attributes synced to this product'
    )

    @api.depends()
    def _compute_icecat_specifications_grouped_dummy(self):
        """Dummy compute method - returns empty to prevent crashes"""
        for product in self:
            product.icecat_specifications_grouped = False

    @api.depends('attribute_line_ids')
    def _compute_icecat_attributes_count(self):
        """Count number of Icecat-sourced attributes"""
        for product in self:
            icecat_attrs = product.attribute_line_ids.filtered(
                lambda l: l.attribute_id.category_id and '[Icecat]' in (l.attribute_id.category_id.name or '')
            )
            product.icecat_attributes_count = len(icecat_attrs)

    def action_sync_with_icecat(self):
        """Manual sync action for selected products"""
        self.ensure_one()
        connector = self.env['icecat.connector']
        
        # Get barcode from first variant that has one
        barcode = self.product_variant_ids.filtered(lambda v: v.barcode)[:1].barcode
        if not barcode:
            raise UserError(_('Product must have a barcode (EAN/GTIN) to sync with Icecat.'))
        
        result = connector.sync_product(self, barcode)
        
        if result.get('success'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Product successfully synced with Icecat'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': result.get('error', _('Unknown error occurred')),
                    'type': 'warning',
                    'sticky': True,
                }
            }

    def action_convert_json_to_attributes(self):
        """
        Convert existing JSON specifications to Odoo attributes
        Useful for migrating products that were synced with old version
        """
        self.ensure_one()
        
        if not self.icecat_specifications_raw:
            raise UserError(_('This product has no JSON specifications to convert.'))
        
        # Parse JSON specs
        import json
        specs_data = self.icecat_specifications_raw if isinstance(self.icecat_specifications_raw, dict) else json.loads(self.icecat_specifications_raw)
        
        # Convert to flat list format expected by _sync_product_attributes
        specifications = []
        for group, specs in specs_data.items():
            for spec in specs:
                specifications.append({
                    'group': group,
                    'name': spec.get('name', ''),
                    'value': spec.get('value', ''),
                    'unit': spec.get('unit', '')
                })
        
        # Sync to attributes
        self.env['icecat.connector']._sync_product_attributes(self, specifications)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'Converted {len(specifications)} specifications to Odoo attributes'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_spec_manager(self):
        """Open the specification manager wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Beheer Specificaties',
            'res_model': 'spec.manager.wizard',
            'view_mode': 'form',
            'target': 'fullscreen',
            'context': {'active_id': self.id},
        }

    @api.model
    def cron_sync_new_products(self):
        """Scheduled action to sync new products in small batches (PRO FEATURE)"""
        # Check if Pro version is installed
        is_pro_installed = self.env['ir.module.module'].search([
            ('name', '=', 'icecat_enrichment_pro_unlock'),
            ('state', '=', 'installed')
        ], limit=1)
        
        if not is_pro_installed:
            _logger.info('Icecat automatic sync disabled - requires Pro version')
            return
        
        IceCatConnector = self.env['icecat.connector']
        
        # Check if auto sync is enabled
        if not self.env['ir.config_parameter'].sudo().get_param(
            'dbw_product_enrichment.auto_sync_enabled', default=True
        ):
            return
        
        batch_size = int(self.env['ir.config_parameter'].sudo().get_param(
                'dbw_product_enrichment.new_product_batch_size', default=10
            ))
        
        # Find products that have variants with barcodes but haven't been synced yet
        products = self.search([
            ('product_variant_ids.barcode', '!=', False),
            ('icecat_sync_status', 'in', ['not_synced', 'pending']),
        ], limit=batch_size, order='create_date desc')
        
        if not products:
            return
        
        # Check if there's already a running log for this sync type
        log = self.env['icecat.sync.log'].search([
            ('sync_type', '=', 'new'),
            ('status', '=', 'running'),
        ], limit=1)
        
        # If no running log exists, create a new one
        if not log:
            log = self.env['icecat.sync.log'].create({
                'sync_type': 'new',
                'total_products': len(products),
                'status': 'running',
                'synced_count': 0,
                'error_count': 0,
                'no_data_count': 0,
            })
            self.env.cr.commit()
        
        synced_count = log.synced_count
        error_count = log.error_count
        no_data_count = log.no_data_count
        
        try:
            for product in products:
                # Add product to processed list
                log.write({'product_ids': [(4, product.id)]})
                
                try:
                    # Get barcode from first variant that has one
                    barcode = product.product_variant_ids.filtered(lambda v: v.barcode)[:1].barcode
                    if not barcode:
                        continue
                    
                    result = IceCatConnector.sync_product(product, barcode)
                    if result.get('success'):
                        synced_count += 1
                    elif product.icecat_sync_status == 'no_data':
                        no_data_count += 1
                    else:
                        error_count += 1
                        log.write({'error_product_ids': [(4, product.id)]})
                except Exception as e:
                    error_count += 1
                    product.write({
                        'icecat_sync_status': 'error',
                        'icecat_error_message': str(e),
                    })
                    log.write({'error_product_ids': [(4, product.id)]})
                
                # Update log after each product to survive timeouts
                log.write({
                    'synced_count': synced_count,
                    'error_count': error_count,
                    'no_data_count': no_data_count,
                })
                self.env.cr.commit()
            
            # Check if there are still products to sync
            remaining_products = self.search_count([
                ('product_variant_ids.barcode', '!=', False),
                ('icecat_sync_status', 'in', ['not_synced', 'pending']),
            ])
            
            # Mark as completed when NO more products need syncing
            if remaining_products == 0:
                log.write({
                    'end_time': fields.Datetime.now(),
                    'status': 'completed',
                })
                self.env.cr.commit()
        except Exception as e:
            log.write({
                'end_time': fields.Datetime.now(),
                'status': 'failed',
                'error_message': str(e),
            })
            self.env.cr.commit()
            raise
        
        return {
            'synced': synced_count,
            'errors': error_count,
            'no_data': no_data_count,
            'total': len(products)
        }

    @api.model
    def cron_update_products(self):
        """Scheduled action to update existing synced products (night run) (PRO FEATURE)"""
        # Check if Pro version is installed
        is_pro_installed = self.env['ir.module.module'].search([
            ('name', '=', 'icecat_enrichment_pro_unlock'),
            ('state', '=', 'installed')
        ], limit=1)
        
        if not is_pro_installed:
            _logger.info('Icecat automatic updates disabled - requires Pro version')
            return
        
        IceCatConnector = self.env['icecat.connector']
        
        # Check if auto sync is enabled
        if not self.env['ir.config_parameter'].sudo().get_param(
            'dbw_product_enrichment.auto_sync_enabled', default=True
        ):
            return
        
        batch_size = int(self.env['ir.config_parameter'].sudo().get_param(
                'dbw_product_enrichment.update_batch_size', default=100
            ))
        
        # Find products that were synced more than 30 days ago
        thirty_days_ago = fields.Datetime.now() - fields.timedelta(days=30)
        
        products = self.search([
            ('product_variant_ids.barcode', '!=', False),
            ('icecat_sync_status', '=', 'synced'),
            '|',
            ('icecat_last_sync', '<', thirty_days_ago),
            ('icecat_last_sync', '=', False),
        ], limit=batch_size, order='icecat_last_sync asc')
        
        if not products:
            return
        
        # Check if there's already a running log for this sync type
        log = self.env['icecat.sync.log'].search([
            ('sync_type', '=', 'update'),
            ('status', '=', 'running'),
        ], limit=1)
        
        # If no running log exists, create a new one
        if not log:
            log = self.env['icecat.sync.log'].create({
                'sync_type': 'update',
                'total_products': len(products),
                'status': 'running',
                'synced_count': 0,
                'error_count': 0,
                'no_data_count': 0,
            })
            self.env.cr.commit()
        
        synced_count = log.synced_count
        error_count = log.error_count
        no_data_count = log.no_data_count
        
        try:
            for product in products:
                # Add product to processed list
                log.write({'product_ids': [(4, product.id)]})
                
                try:
                    # Get barcode from first variant that has one
                    barcode = product.product_variant_ids.filtered(lambda v: v.barcode)[:1].barcode
                    if not barcode:
                        continue
                    
                    result = IceCatConnector.sync_product(product, barcode)
                    if result.get('success'):
                        synced_count += 1
                    elif product.icecat_sync_status == 'no_data':
                        no_data_count += 1
                    else:
                        error_count += 1
                        log.write({'error_product_ids': [(4, product.id)]})
                except Exception as e:
                    error_count += 1
                    product.write({
                        'icecat_sync_status': 'error',
                        'icecat_error_message': str(e),
                    })
                    log.write({'error_product_ids': [(4, product.id)]})
                
                # Update log after each product to survive timeouts
                log.write({
                    'synced_count': synced_count,
                    'error_count': error_count,
                    'no_data_count': no_data_count,
                })
                self.env.cr.commit()
            
            # Check if there are still products to update
            thirty_days_ago = fields.Datetime.now() - fields.timedelta(days=30)
            remaining_products = self.search_count([
                ('product_variant_ids.barcode', '!=', False),
                ('icecat_sync_status', '=', 'synced'),
                '|',
                ('icecat_last_sync', '<', thirty_days_ago),
                ('icecat_last_sync', '=', False),
            ])
            
            # Mark as completed when NO more products need updating
            if remaining_products == 0:
                log.write({
                    'end_time': fields.Datetime.now(),
                    'status': 'completed',
                })
                self.env.cr.commit()
        except Exception as e:
            log.write({
                'end_time': fields.Datetime.now(),
                'status': 'failed',
                'error_message': str(e),
            })
            self.env.cr.commit()
            raise
        
        return {
            'synced': synced_count,
            'errors': error_count,
            'no_data': no_data_count,
            'total': len(products)
        }
