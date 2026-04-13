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
            wizard.product_count = len(wizard._get_products_to_sync())

    def _has_sync_identifier(self, product):
        """A product is sync-eligible when it has:
        - an EAN/barcode on template/variant, OR
        - a SKU (default_code) + brand (product_brand_id or icecat_brand)
        """
        barcode = (product.barcode or '').strip()
        if not barcode:
            variant_with_barcode = product.product_variant_ids.filtered(lambda v: v.barcode)[:1]
            barcode = (variant_with_barcode.barcode or '').strip() if variant_with_barcode else ''

        if barcode:
            return True

        sku = (product.default_code or '').strip()
        if not sku:
            variant_with_sku = product.product_variant_ids.filtered(lambda v: v.default_code)[:1]
            sku = (variant_with_sku.default_code or '').strip() if variant_with_sku else ''

        brand_name = ''
        if 'product_brand_id' in product._fields and product.product_brand_id:
            brand_name = (product.product_brand_id.name or '').strip()
        if not brand_name:
            brand_name = (product.icecat_brand or '').strip()

        return bool(sku and brand_name)

    def _get_products_to_sync(self):
        """Return sync candidates for selected sync_type, filtered on supported identifiers."""
        Product = self.env['product.template']

        if self.sync_type == 'selected':
            product_ids = self.env.context.get('active_ids', [])
            products = Product.browse(product_ids).exists()
        elif self.sync_type == 'all_not_synced':
            products = Product.search([
                ('icecat_sync_status', 'in', ['not_synced', 'pending'])
            ])
        elif self.sync_type == 'all_with_errors':
            products = Product.search([
                ('icecat_sync_status', '=', 'error')
            ])
        elif self.sync_type == 'all_outdated':
            thirty_days_ago = fields.Datetime.now() - fields.timedelta(days=30)
            products = Product.search([
                ('icecat_sync_status', '=', 'synced'),
                '|',
                ('icecat_last_sync', '<', thirty_days_ago),
                ('icecat_last_sync', '=', False),
            ])
        else:
            products = Product.browse()

        return products.filtered(self._has_sync_identifier)

    def _get_product_domain(self):
        """Get domain based on sync type"""
        return [('id', 'in', self._get_products_to_sync().ids)]

    def _get_log_sync_type(self):
        if self.sync_type == 'all_not_synced':
            return 'new'
        if self.sync_type == 'all_outdated':
            return 'update'
        return 'manual'

    def action_sync_products(self):
        """Execute the bulk sync"""
        self.ensure_one()
        
        # Check if Pro version is required for this operation
        if self.sync_type != 'selected':
            is_pro_installed = self.env['ir.module.module'].search([
                ('name', '=', 'icecat_enrichment_pro_unlock'),
                ('state', '=', 'installed')
            ], limit=1)
            
            if not is_pro_installed:
                raise UserError(
                    'Bulk sync operations require Icecat Pro.\n\n'
                    'FREE version: Manual sync of selected products only\n'
                    'PRO version unlocks:\n'
                    '  ✓ Automatic scheduled syncs (every 4 hours + nightly updates)\n'
                    '  ✓ Bulk sync all products not yet synced\n'
                    '  ✓ Bulk retry all products with errors\n'
                    '  ✓ Bulk update all outdated products\n'
                    '  ✓ Dashboard statistics\n\n'
                    'Upgrade to Pro: €199 one-time purchase\n'
                    'Contact: support@nerbys.nl'
                )
        
        # Get products to sync (all candidates, processed in chunks of batch_size)
        products = self._get_products_to_sync().sorted(key=lambda p: p.id)
        
        if not products:
            raise UserError(_('No products found to synchronize.'))

        chunk_size = max(1, int(self.batch_size or 1))
        
        # Perform sync
        IceCatConnector = self.env['icecat.connector']
        SyncLog = self.env['icecat.sync.log']

        sync_log = SyncLog.create({
            'sync_type': self._get_log_sync_type(),
            'total_products': len(products),
            'status': 'running',
            'synced_count': 0,
            'error_count': 0,
            'no_data_count': 0,
        })
        self.env.cr.commit()
        
        synced_count = 0
        error_count = 0
        no_data_count = 0
        
        try:
            for start in range(0, len(products), chunk_size):
                batch_products = products[start:start + chunk_size]
                for product in batch_products:
                    sync_log.write({'product_ids': [(4, product.id)]})
                    try:
                        result = IceCatConnector.sync_product(product)
                        if result.get('success'):
                            synced_count += 1
                        elif product.icecat_sync_status == 'no_data':
                            no_data_count += 1
                        else:
                            error_count += 1
                            sync_log.write({'error_product_ids': [(4, product.id)]})
                    except Exception as e:
                        error_count += 1
                        product.write({
                            'icecat_sync_status': 'error',
                            'icecat_error_message': str(e),
                        })
                        sync_log.write({'error_product_ids': [(4, product.id)]})

                sync_log.write({
                    'synced_count': synced_count,
                    'error_count': error_count,
                    'no_data_count': no_data_count,
                })

                # Commit per chunk to keep transactions manageable on large runs
                self.env.cr.commit()

            sync_log.write({
                'synced_count': synced_count,
                'error_count': error_count,
                'no_data_count': no_data_count,
                'status': 'completed',
                'end_time': fields.Datetime.now(),
            })
            self.env.cr.commit()
        except Exception as e:
            sync_log.write({
                'synced_count': synced_count,
                'error_count': error_count,
                'no_data_count': no_data_count,
                'status': 'failed',
                'error_message': str(e),
                'end_time': fields.Datetime.now(),
            })
            self.env.cr.commit()
            raise
        
        # Show result message
        processed_count = len(products)
        batch_count = (processed_count + chunk_size - 1) // chunk_size

        message = _('Synchronization completed:\n')
        message += _('- Processed: %s products in %s batches\n') % (processed_count, batch_count)
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
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
