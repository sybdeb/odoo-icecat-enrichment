# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class EnrichmentFieldMapping(models.Model):
    _name = 'enrichment.field.mapping'
    _description = 'Field Mapping Configuration for Product Enrichment'
    _order = 'sequence, field_name'

    sequence = fields.Integer(string='Sequence', default=10)
    field_name = fields.Selection([
        ('name', 'Product Naam'),
        ('description_sale', 'Verkoopbeschrijving'),
        ('website_description', 'Website Beschrijving'),
        ('image_1920', 'Productafbeelding'),
    ], string='Veld', required=True)
    
    allow_barcodelookup = fields.Boolean(
        string='BarcodeLookup Toestaan',
        default=True,
        help='Sta toe dat BarcodeLookup dit veld mag vullen/updaten'
    )
    allow_icecat = fields.Boolean(
        string='Icecat Toestaan',
        default=True,
        help='Sta toe dat Icecat dit veld mag vullen/updaten'
    )
    allow_overwrite = fields.Boolean(
        string='Overschrijven Toestaan',
        default=False,
        help='Sta toe dat een bron een reeds gevuld veld mag overschrijven'
    )
    
    notes = fields.Text(string='Notities')

    _sql_constraints = [
        ('field_name_unique', 'unique(field_name)', 'Elk veld kan maar één mapping hebben!')
    ]
