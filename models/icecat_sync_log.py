# -*- coding: utf-8 -*-

from odoo import api, fields, models


class IcecatSyncLog(models.Model):
    _name = 'icecat.sync.log'
    _description = 'Icecat Synchronization Log'
    _order = 'create_date desc'

    name = fields.Char(string='Sync Run', compute='_compute_name', store=True)
    sync_type = fields.Selection([
        ('new', 'New Products'),
        ('update', 'Update Products'),
        ('manual', 'Manual Sync'),
    ], string='Sync Type', required=True)
    start_time = fields.Datetime(string='Start Time', default=fields.Datetime.now)
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(string='Duration (seconds)', compute='_compute_duration', store=True)
    total_products = fields.Integer(string='Total Products')
    synced_count = fields.Integer(string='Successfully Synced')
    error_count = fields.Integer(string='Errors')
    no_data_count = fields.Integer(string='No Data Available')
    status = fields.Selection([
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Status', default='running')
    error_message = fields.Text(string='Error Message')

    @api.depends('start_time', 'sync_type')
    def _compute_name(self):
        for record in self:
            if record.start_time:
                record.name = f"{dict(record._fields['sync_type'].selection)[record.sync_type]} - {record.start_time.strftime('%Y-%m-%d %H:%M')}"
            else:
                record.name = f"{dict(record._fields['sync_type'].selection)[record.sync_type]}"

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration = delta.total_seconds()
            else:
                record.duration = 0.0
