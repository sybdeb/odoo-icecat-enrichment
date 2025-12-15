# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json


class SpecManagerWizard(models.TransientModel):
    _name = 'spec.manager.wizard'
    _description = 'Specificatie Manager'

    product_id = fields.Many2one('product.template', string='Product', required=True)
    spec_line_ids = fields.One2many('spec.manager.line', 'wizard_id', string='Specificaties')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            product = self.env['product.template'].browse(active_id)
            res['product_id'] = active_id

            # Parse specifications and create lines
            lines = []
            if product.icecat_specifications_raw:
                # Handle both string (JSON) and dict/list (already parsed)
                if isinstance(product.icecat_specifications_raw, str):
                    specs = json.loads(product.icecat_specifications_raw)
                else:
                    specs = product.icecat_specifications_raw
                
                # Check if specs is a dict (grouped) or list (flat)
                if isinstance(specs, dict):
                    for group_name, group_specs in specs.items():
                        for spec in group_specs:
                            lines.append((0, 0, {
                                'group_name': group_name,
                                'spec_name': spec.get('name', ''),
                                'spec_value': spec.get('value', ''),
                                'spec_unit': spec.get('unit', ''),
                                'to_delete': False,
                            }))
                elif isinstance(specs, list):
                    # Flat list of specs without groups
                    for spec in specs:
                        lines.append((0, 0, {
                            'group_name': spec.get('group', 'General'),
                            'spec_name': spec.get('name', ''),
                            'spec_value': spec.get('value', ''),
                            'spec_unit': spec.get('unit', ''),
                            'to_delete': False,
                        }))
            res['spec_line_ids'] = lines
        return res

    def action_apply(self):
        """Apply changes: remove marked specs and update product"""
        if not self.product_id:
            return

        # Get current specs
        if not self.product_id.icecat_specifications_raw:
            return

        # Handle both string (JSON) and dict/list (already parsed)
        if isinstance(self.product_id.icecat_specifications_raw, str):
            specs = json.loads(self.product_id.icecat_specifications_raw)
        else:
            specs = self.product_id.icecat_specifications_raw

        # Get specs to keep (not marked for deletion)
        specs_to_keep = self.spec_line_ids.filtered(lambda l: not l.to_delete)

        # Rebuild specs dict
        new_specs = {}
        for line in specs_to_keep:
            if line.group_name not in new_specs:
                new_specs[line.group_name] = []
            new_specs[line.group_name].append({
                'name': line.spec_name,
                'value': line.spec_value,
                'unit': line.spec_unit,
            })

        # Update product
        self.product_id.icecat_specifications_raw = json.dumps(new_specs) if new_specs else False

        return {'type': 'ir.actions.act_window_close'}


class SpecManagerLine(models.TransientModel):
    _name = 'spec.manager.line'
    _description = 'Specificatie Regel'

    wizard_id = fields.Many2one('spec.manager.wizard', string='Wizard', required=True, ondelete='cascade')
    group_name = fields.Char(string='Groep', readonly=True)
    spec_name = fields.Char(string='Specificatie', readonly=True)
    spec_value = fields.Char(string='Waarde', readonly=True)
    spec_unit = fields.Char(string='Eenheid', readonly=True)
    to_delete = fields.Boolean(string='Verwijderen', default=False)
