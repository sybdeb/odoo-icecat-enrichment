# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class IcecatSyncWizard(models.TransientModel):
    _name = 'icecat.sync.wizard'
    _description = 'Icecat Bulk Sync Wizard'

    sync_type = fields.Selection([
        ('selected', 'Selected Products Only'),
        ('all_not_synced', 'All Products Not Yet Synced'),
        ('all_with_errors', 'All Products with Sync Errors'),
        ('all_outdated', 'All Products (Update Synced > 30 Days Ago)'),
    ], string='Sync Type', required=True, default='selected')
    
    batch_size = fields.Integer(
        string='Batch Size',
        default=10,
        help='Number of products to process in this batch'
    )
    
    product_count = fields.Integer(
        string='Products to Sync',
        compute='_compute_product_count',
        readonly=True
    )

    @api.depends('sync_type')
    def _compute_product_count(self):
        for wizard in self:
            domain = wizard._get_product_domain()
            wizard.product_count = self.env['product.template'].search_count(domain)

    def _get_product_domain(self):
        """Get domain based on sync type"""
        if self.sync_type == 'selected':
            product_ids = self.env.context.get('active_ids', [])
            return [('id', 'in', product_ids), ('barcode', '!=', False)]
        elif self.sync_type == 'all_not_synced':
            return [('barcode', '!=', False), ('icecat_sync_status', 'in', ['not_synced', 'pending'])]
        elif self.sync_type == 'all_with_errors':
            return [('barcode', '!=', False), ('icecat_sync_status', '=', 'error')]
        elif self.sync_type == 'all_outdated':
            thirty_days_ago = fields.Datetime.now() - fields.timedelta(days=30)
            return [
                ('barcode', '!=', False),
                ('icecat_sync_status', '=', 'synced'),
                '|',
                ('icecat_last_sync', '<', thirty_days_ago),
                ('icecat_last_sync', '=', False),
            ]
        return []

    def action_sync_products(self):
        """Execute the bulk sync"""
        self.ensure_one()
        
        # Get products to sync
        domain = self._get_product_domain()
        products = self.env['product.template'].search(domain, limit=self.batch_size)
        
        if not products:
            raise UserError(_('No products found to synchronize.'))
        
        # Perform sync
        IceCatConnector = self.env['icecat.connector']
        
        synced_count = 0
        error_count = 0
        no_data_count = 0
        
        for product in products:
            try:
                result = IceCatConnector.sync_product(product)
                if result.get('success'):
                    synced_count += 1
                elif product.icecat_sync_status == 'no_data':
                    no_data_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                product.write({
                    'icecat_sync_status': 'error',
                    'icecat_error_message': str(e),
                })
        
        # Show result message
        message = _('Synchronization completed:\n')
        message += _('- Successfully synced: %s\n') % synced_count
        message += _('- No data available: %s\n') % no_data_count
        message += _('- Errors: %s') % error_count
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Icecat Sync Completed'),
                'message': message,
                'type': 'success' if error_count == 0 else 'warning',
                'sticky': True,
            }
        }
