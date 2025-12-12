# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class EnrichmentSyncLog(models.Model):
    _name = 'enrichment.sync.log'
    _description = 'Product Enrichment Sync Log'
    _order = 'start_time desc'

    name = fields.Char(string='Log Naam', compute='_compute_name', store=True)
    sync_type = fields.Selection([
        ('manual', 'Handmatig'),
        ('new', 'Nieuwe Producten'),
        ('update', 'Update Bestaande'),
    ], string='Sync Type', required=True, default='manual')
    
    start_time = fields.Datetime(string='Start Tijd', default=fields.Datetime.now, required=True)
    end_time = fields.Datetime(string='Eind Tijd')
    
    total_products = fields.Integer(string='Totaal Producten')
    synced_count = fields.Integer(string='Succesvol Verrijkt')
    error_count = fields.Integer(string='Errors')
    no_data_count = fields.Integer(string='Geen Data')
    
    status = fields.Selection([
        ('running', 'Bezig'),
        ('completed', 'Voltooid'),
        ('failed', 'Mislukt'),
    ], string='Status', default='running')
    
    error_message = fields.Text(string='Error Bericht')
    sources_used = fields.Char(string='Gebruikte Bronnen')

    @api.depends('sync_type', 'start_time')
    def _compute_name(self):
        for record in self:
            if record.start_time:
                record.name = f"{dict(record._fields['sync_type'].selection).get(record.sync_type, '')} - {record.start_time.strftime('%Y-%m-%d %H:%M')}"
            else:
                record.name = f"{dict(record._fields['sync_type'].selection).get(record.sync_type, '')}"
