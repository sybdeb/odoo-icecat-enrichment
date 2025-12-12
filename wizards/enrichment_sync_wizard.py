# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class EnrichmentSyncWizard(models.TransientModel):
    _name = 'enrichment.sync.wizard'
    _description = 'Bulk Product Enrichment Wizard'

    product_ids = fields.Many2many(
        'product.template',
        string='Producten',
        required=True,
        help='Producten om te verrijken'
    )
    total_products = fields.Integer(
        string='Totaal Producten',
        compute='_compute_total_products'
    )
    force_update = fields.Boolean(
        string='Forceer Update',
        default=False,
        help='Update ook producten die al verrijkt zijn'
    )
    source_override = fields.Selection([
        ('use_config', 'Gebruik Configuratie'),
        ('barcodelookup_only', 'Alleen BarcodeLookup'),
        ('icecat_only', 'Alleen Icecat'),
        ('both', 'Beide Bronnen'),
    ], string='Bron Override',
        default='use_config',
        help='Override de geconfigureerde bron prioriteit voor deze actie'
    )

    @api.depends('product_ids')
    def _compute_total_products(self):
        for wizard in self:
            wizard.total_products = len(wizard.product_ids)

    def action_enrich_products(self):
        """Enrich selected products"""
        self.ensure_one()
        
        enrichment_manager = self.env['enrichment.manager']
        
        # Filter products with barcodes
        products_with_barcode = self.product_ids.filtered(
            lambda p: p.product_variant_ids.filtered(lambda v: v.barcode)
        )
        
        if not products_with_barcode:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Waarschuwing'),
                    'message': _('Geen van de geselecteerde producten heeft een barcode'),
                    'type': 'warning',
                    'sticky': True,
                }
            }
        
        # Create log entry
        log = self.env['enrichment.sync.log'].create({
            'sync_type': 'manual',
            'total_products': len(products_with_barcode),
            'status': 'running',
        })
        
        synced_count = 0
        error_count = 0
        no_data_count = 0
        all_sources = set()
        
        # Temporarily override source priority if requested
        original_priority = None
        if self.source_override != 'use_config':
            original_priority = self.env['ir.config_parameter'].sudo().get_param(
                'product_content_verrijking.source_priority'
            )
            if self.source_override == 'barcodelookup_only':
                self.env['ir.config_parameter'].sudo().set_param(
                    'product_content_verrijking.source_priority', 'barcodelookup_only'
                )
            elif self.source_override == 'icecat_only':
                self.env['ir.config_parameter'].sudo().set_param(
                    'product_content_verrijking.source_priority', 'icecat_only'
                )
            elif self.source_override == 'both':
                self.env['ir.config_parameter'].sudo().set_param(
                    'product_content_verrijking.source_priority', 'barcodelookup_first'
                )
        
        try:
            for product in products_with_barcode:
                # Skip already enriched products unless force_update is set
                if not self.force_update and product.enrichment_status == 'synced':
                    continue
                
                # Get barcode
                barcode = product.product_variant_ids.filtered(lambda v: v.barcode)[:1].barcode
                if not barcode:
                    continue
                
                try:
                    result = enrichment_manager.enrich_product(product, barcode)
                    if result.get('success'):
                        synced_count += 1
                        if result.get('sources'):
                            all_sources.update(result['sources'])
                    elif product.enrichment_status == 'no_data':
                        no_data_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
                    product.write({
                        'enrichment_status': 'error',
                        'enrichment_error_message': str(e),
                    })
            
            # Update log
            log.write({
                'end_time': fields.Datetime.now(),
                'synced_count': synced_count,
                'error_count': error_count,
                'no_data_count': no_data_count,
                'status': 'completed',
                'sources_used': ', '.join(all_sources) if all_sources else '',
            })
            
        finally:
            # Restore original priority if it was overridden
            if original_priority is not None:
                self.env['ir.config_parameter'].sudo().set_param(
                    'product_content_verrijking.source_priority', original_priority
                )
        
        # Show result
        message = _(
            'Verrijking voltooid!\n'
            'Succesvol: %s\n'
            'Geen data: %s\n'
            'Errors: %s\n'
            'Bronnen gebruikt: %s'
        ) % (synced_count, no_data_count, error_count, ', '.join(all_sources) if all_sources else 'geen')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Verrijking Voltooid'),
                'message': message,
                'type': 'success' if error_count == 0 else 'warning',
                'sticky': True,
            }
        }
