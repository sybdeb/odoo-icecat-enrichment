# -*- coding: utf-8 -*-
from odoo import fields, models

class ProductImage(models.Model):
    _inherit = 'product.image'

    icecat_url = fields.Char(string="Icecat Image URL", help="Voor deduplicatie bij sync")