# -*- coding: utf-8 -*-

from collections import defaultdict
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

    icecat_specifications_raw = fields.Json(
        string='Icecat Specifications Raw',
        help='Raw specifications data from Icecat, stored as JSON'
    )

    icecat_specifications_grouped = fields.Html(
        string='Gegroepeerde Specificaties',
        compute='_compute_icecat_specifications_grouped',
        store=False,
        help='Specificaties gegroepeerd per categorie voor website accordion'
    )

    icecat_highlights_html = fields.Html(
        string='Icecat Highlights',
        help='Product highlights/features from Icecat in HTML format'
    )

    @api.depends('icecat_specifications_raw')
    def _compute_icecat_specifications_grouped(self):
        """Genereer HTML voor accordion per Icecat-categorie"""
        for product in self:
            if not product.icecat_specifications_raw:
                product.icecat_specifications_grouped = False
                continue

            specs_html = ''
            specs_data = product.icecat_specifications_raw

            # Handle both dict (grouped) and list (flat) formats
            if isinstance(specs_data, dict):
                # Already grouped format
                for group_name, specs_list in specs_data.items():
                    specs_html += f'''
                        <div class="specs-section">
                            <h4 class="specs-group-title">{group_name}</h4>
                            <table class="table table-sm table-striped specs-table">
                                <tbody>
                    '''
                    for spec in specs_list:
                        name = spec.get('name', '')
                        value = spec.get('value', '')
                        unit = spec.get('unit', '')
                        value_with_unit = f"{value} {unit}".strip() if unit else value
                        specs_html += f'''
                                    <tr>
                                        <td class="spec-key"><strong>{name}</strong></td>
                                        <td class="spec-value">{value_with_unit}</td>
                                    </tr>
                        '''
                    specs_html += '''
                                </tbody>
                            </table>
                        </div>
                    '''
            elif isinstance(specs_data, list):
                # Flat list - group by 'group' field
                grouped_specs = defaultdict(list)
                for spec in specs_data:
                    group = spec.get('group', 'Algemeen')
                    grouped_specs[group].append(spec)

                for group_name, specs_list in grouped_specs.items():
                    specs_html += f'''
                        <div class="specs-section">
                            <h4 class="specs-group-title">{group_name}</h4>
                            <table class="table table-sm table-striped specs-table">
                                <tbody>
                    '''
                    for spec in specs_list:
                        name = spec.get('name', '')
                        value = spec.get('value', '')
                        unit = spec.get('unit', '')
                        value_with_unit = f"{value} {unit}".strip() if unit else value
                        specs_html += f'''
                                    <tr>
                                        <td class="spec-key"><strong>{name}</strong></td>
                                        <td class="spec-value">{value_with_unit}</td>
                                    </tr>
                        '''
                    specs_html += '''
                                </tbody>
                            </table>
                        </div>
                    '''

            product.icecat_specifications_grouped = specs_html if specs_html else False

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

    @api.model
    def cron_sync_new_products(self):
        """Scheduled action to sync new products in small batches"""
        IceCatConnector = self.env['icecat.connector']
        
        # Check if auto sync is enabled
        if not self.env['ir.config_parameter'].sudo().get_param(
            'product_content_verrijking.auto_sync_enabled', default=True
        ):
            return
        
        batch_size = int(self.env['ir.config_parameter'].sudo().get_param(
            'product_content_verrijking.new_product_batch_size', default=10
        ))
        
        # Find products that have variants with barcodes but haven't been synced yet
        products = self.search([
            ('product_variant_ids.barcode', '!=', False),
            ('icecat_sync_status', 'in', ['not_synced', 'pending']),
        ], limit=batch_size, order='create_date desc')
        
        if not products:
            return
        
        # Close any old running logs for this type (they timed out or crashed)
        old_running_logs = self.env['icecat.sync.log'].search([
            ('sync_type', '=', 'new'),
            ('status', '=', 'running'),
        ])
        for old_log in old_running_logs:
            old_log.write({
                'end_time': fields.Datetime.now(),
                'status': 'completed',
            })
        
        # Create new log entry with immediate commit
        log = self.env['icecat.sync.log'].create({
            'sync_type': 'new',
            'total_products': len(products),
            'status': 'running',
        })
        self.env.cr.commit()  # Commit log immediately so it's visible even if cron times out
        
        synced_count = 0
        error_count = 0
        no_data_count = 0
        
        try:
            for product in products:
                try:
                    # Track this product in the log
                    log.write({'product_ids': [(4, product.id)]})
                    
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
                    
                    # Commit after each product to save progress
                    self.env.cr.commit()
                except Exception as e:
                    error_count += 1
                    log.write({'error_product_ids': [(4, product.id)]})
                    product.write({
                        'icecat_sync_status': 'error',
                        'icecat_error_message': str(e),
                    })
                    self.env.cr.commit()
            
            # Update log
            log.write({
                'end_time': fields.Datetime.now(),
                'synced_count': synced_count,
                'error_count': error_count,
                'no_data_count': no_data_count,
                'status': 'completed',
            })
            self.env.cr.commit()
        except Exception as e:
            log.write({
                'end_time': fields.Datetime.now(),
                'synced_count': synced_count,
                'error_count': error_count,
                'no_data_count': no_data_count,
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
        """Scheduled action to update existing synced products (night run)"""
        IceCatConnector = self.env['icecat.connector']
        
        # Check if auto sync is enabled
        if not self.env['ir.config_parameter'].sudo().get_param(
            'product_content_verrijking.auto_sync_enabled', default=True
        ):
            return
        
        batch_size = int(self.env['ir.config_parameter'].sudo().get_param(
            'product_content_verrijking.update_batch_size', default=100
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
        
        # Close any old running logs for this type (they timed out or crashed)
        old_running_logs = self.env['icecat.sync.log'].search([
            ('sync_type', '=', 'update'),
            ('status', '=', 'running'),
        ])
        for old_log in old_running_logs:
            old_log.write({
                'end_time': fields.Datetime.now(),
                'status': 'completed',
            })
        
        # Create new log entry with immediate commit
        log = self.env['icecat.sync.log'].create({
            'sync_type': 'update',
            'total_products': len(products),
            'status': 'running',
        })
        self.env.cr.commit()  # Commit log immediately so it's visible even if cron times out
        
        synced_count = 0
        error_count = 0
        no_data_count = 0
        
        try:
            for product in products:
                try:
                    # Track this product in the log
                    log.write({'product_ids': [(4, product.id)]})
                    
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
                    
                    # Commit after each product to save progress
                    self.env.cr.commit()
                except Exception as e:
                    error_count += 1
                    log.write({'error_product_ids': [(4, product.id)]})
                    product.write({
                        'icecat_sync_status': 'error',
                        'icecat_error_message': str(e),
                    })
                    self.env.cr.commit()
            
            # Update log
            log.write({
                'end_time': fields.Datetime.now(),
                'synced_count': synced_count,
                'error_count': error_count,
                'no_data_count': no_data_count,
                'status': 'completed',
            })
            self.env.cr.commit()
        except Exception as e:
            log.write({
                'end_time': fields.Datetime.now(),
                'synced_count': synced_count,
                'error_count': error_count,
                'no_data_count': no_data_count,
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
