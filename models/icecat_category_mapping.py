# -*- coding: utf-8 -*-

import re
from difflib import SequenceMatcher

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class IcecatCategoryMapping(models.Model):
    _name = 'icecat.category.mapping'
    _description = 'Icecat to Odoo Category Mapping'
    _rec_name = 'icecat_category'

    icecat_category = fields.Char(
        string='Icecat Category',
        required=True,
        help='Category name from Icecat'
    )
    odoo_category_id = fields.Many2one(
        'product.public.category',
        string='Website Category',
        help='Odoo website product category'
    )
    internal_category_id = fields.Many2one(
        'product.category',
        string='Internal Category',
        help='Odoo internal product category'
    )
    auto_publish = fields.Boolean(
        string='Auto Publish to Website',
        default=True,
        help='Automatically publish products to website when synced'
    )
    product_count = fields.Integer(
        string='Products',
        compute='_compute_product_count',
        help='Number of products with this Icecat category'
    )

    _sql_constraints = [
        ('icecat_category_unique', 'unique(icecat_category)', 
         'This Icecat category already has a mapping!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._guard_mass_same_website_category()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'odoo_category_id' in vals and vals.get('odoo_category_id'):
            self._guard_mass_same_website_category()
        return result

    def _guard_mass_same_website_category(self):
        """Prevent accidental mass overwrite to one website category."""
        if self.env.context.get('icecat_allow_mass_category_write'):
            return

        total_mappings = self.search_count([('icecat_category', '!=', False)])
        if total_mappings < 20:
            return

        grouped = self.read_group(
            [('odoo_category_id', '!=', False)],
            ['odoo_category_id'],
            ['odoo_category_id'],
            lazy=False,
        )
        grouped = [g for g in grouped if g.get('odoo_category_id')]
        if not grouped:
            return

        dominant = max(grouped, key=lambda g: g['odoo_category_id_count'])
        dominant_count = dominant['odoo_category_id_count']
        if dominant_count >= int(total_mappings * 0.8):
            category_name = dominant['odoo_category_id'][1]
            raise UserError(_(
                'Blocked: %(count)s/%(total)s mappings point to "%(category)s". '
                'This looks like an accidental bulk overwrite.'
            ) % {
                'count': dominant_count,
                'total': total_mappings,
                'category': category_name,
            })

    @api.depends('icecat_category')
    def _compute_product_count(self):
        """Count products with this Icecat category"""
        for mapping in self:
            mapping.product_count = self.env['product.template'].search_count([
                ('icecat_category', '=', mapping.icecat_category)
            ])

    @api.model
    def get_mapping(self, icecat_category):
        """Get mapping for an Icecat category, create default if not exists"""
        if not icecat_category:
            return None
        
        mapping = self.search([('icecat_category', '=', icecat_category)], limit=1)
        
        if not mapping:
            # Create a basic mapping
            mapping = self.create({
                'icecat_category': icecat_category,
                'auto_publish': True,  # Auto-publish by default
            })
        
        return mapping

    @api.model
    def _create_category_hierarchy(self, category_path, model_name):
        """
        Create a category hierarchy from a path like 'Electronics > Computers > Monitors'
        Returns the deepest (leaf) category
        """
        if not category_path:
            return None
        
        # Split the path by ' > '
        parts = [part.strip() for part in category_path.split('>')]
        
        parent = None
        category_obj = self.env[model_name]
        
        for part in parts:
            # Search for existing category with this name and parent
            domain = [('name', '=', part)]
            if parent:
                domain.append(('parent_id', '=', parent.id))
            else:
                domain.append(('parent_id', '=', False))
            
            category = category_obj.search(domain, limit=1)
            
            if not category:
                # Create the category
                vals = {'name': part}
                if parent:
                    vals['parent_id'] = parent.id
                category = category_obj.create(vals)
            
            parent = category
        
        return parent  # Return the deepest category

    @api.model
    def apply_mapping(self, product, icecat_category):
        """Apply category mapping to a product"""
        mapping = self.get_mapping(icecat_category)
        
        if not mapping:
            return {}
        
        if not product:
            return {}

        return mapping._prepare_product_mapping_vals(product)

    def _get_managed_public_category_ids(self):
        """Return website categories managed by Icecat mappings."""
        self.ensure_one()
        return set(
            self.search([('odoo_category_id', '!=', False)]).mapped('odoo_category_id').ids
        )

    def _prepare_product_mapping_vals(self, product):
        """Build write values for one product based on this mapping."""
        self.ensure_one()

        vals = {}

        # Website category: replace only Icecat-managed categories,
        # keep manually assigned non-Icecat website categories untouched.
        if self.odoo_category_id and 'public_categ_ids' in product._fields:
            managed_ids = self._get_managed_public_category_ids()
            current_ids = set(product.public_categ_ids.ids)
            kept_ids = list(current_ids - managed_ids)
            vals['public_categ_ids'] = [(6, 0, kept_ids + [self.odoo_category_id.id])]

        # Internal category
        if self.internal_category_id and 'categ_id' in product._fields:
            vals['categ_id'] = self.internal_category_id.id

        # Website publish
        if self.auto_publish and 'is_published' in product._fields:
            vals['is_published'] = True

        return vals

    def action_apply_to_products(self):
        """Apply this mapping to all products with this Icecat category"""
        self.ensure_one()

        if not self.odoo_category_id and not self.internal_category_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No target category configured'),
                    'message': _('Set a Website Category and/or Internal Category before applying to products.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Safety check: block mass-apply when one website category dominates almost all mappings.
        # This usually indicates accidental bulk edits in the mapping table.
        if self.odoo_category_id:
            total_mapped = self.search_count([('odoo_category_id', '!=', False)])
            same_category_count = self.search_count([('odoo_category_id', '=', self.odoo_category_id.id)])
            if total_mapped >= 20 and same_category_count >= int(total_mapped * 0.8):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Safety block active'),
                        'message': _(
                            'Apply blocked: %(same)s/%(total)s mappings point to "%(category)s". '
                            'First verify and correct Category Mappings to avoid mass misassignment.'
                        ) % {
                            'same': same_category_count,
                            'total': total_mapped,
                            'category': self.odoo_category_id.display_name,
                        },
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        
        # Find all products with this Icecat category
        products = self.env['product.template'].search([
            ('icecat_category', '=', self.icecat_category)
        ])
        
        if not products:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Products'),
                    'message': _('No products found with this Icecat category.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Apply mapping per product (ensures safe replacement behavior for website categories)
        applied_count = 0
        for product in products:
            vals = self._prepare_product_mapping_vals(product)
            if vals:
                product.write(vals)
                applied_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Mapping applied to %d products (category: %s).') % (applied_count, self.icecat_category),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reset_dominant_website_category(self):
        """
        Recovery action:
        - Detect dominant website category across mappings
        - Clear it from affected mappings
        - Remove it from products linked to those Icecat categories
        """
        self.ensure_one()

        mapped_domain = [('odoo_category_id', '!=', False)]
        total_mapped = self.search_count(mapped_domain)
        if not total_mapped:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Nothing to reset'),
                    'message': _('No mappings with a Website Category were found.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        grouped = self.read_group(mapped_domain, ['odoo_category_id'], ['odoo_category_id'], lazy=False)
        grouped = [g for g in grouped if g.get('odoo_category_id')]
        if not grouped:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Nothing to reset'),
                    'message': _('No valid Website Category values found in mappings.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        dominant = max(grouped, key=lambda g: g['odoo_category_id_count'])
        dominant_category_id = dominant['odoo_category_id'][0]
        dominant_category_name = dominant['odoo_category_id'][1]
        dominant_count = dominant['odoo_category_id_count']

        # Safety: only run if dominance is significant, to avoid accidental cleanup.
        if dominant_count < int(total_mapped * 0.5):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Reset blocked'),
                    'message': _(
                        'No dominant category found (top: %(top)s/%(total)s). Recovery reset only runs when one category dominates at least 50%%.'
                    ) % {
                        'top': dominant_count,
                        'total': total_mapped,
                    },
                    'type': 'warning',
                    'sticky': True,
                }
            }

        affected_mappings = self.search([('odoo_category_id', '=', dominant_category_id)])
        affected_icecat_categories = affected_mappings.mapped('icecat_category')

        # 1) Reset mapping values (keep internal categories untouched)
        affected_mappings.write({'odoo_category_id': False})

        # 2) Remove dominant website category from affected products
        product_domain = [
            ('icecat_category', 'in', affected_icecat_categories),
            ('public_categ_ids', 'in', [dominant_category_id]),
        ]
        affected_products = self.env['product.template'].search(product_domain)
        if affected_products:
            affected_products.write({'public_categ_ids': [(3, dominant_category_id)]})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Recovery completed'),
                'message': _(
                    'Reset website category "%(category)s" in %(mappings)s mappings and removed it from %(products)s products.'
                ) % {
                    'category': dominant_category_name,
                    'mappings': len(affected_mappings),
                    'products': len(affected_products),
                },
                'type': 'success',
                'sticky': True,
            }
        }

    @api.model
    def _normalize_category_text(self, text):
        value = (text or '').strip().lower()
        value = re.sub(r'\s+', ' ', value)
        return value

    @api.model
    def _find_best_public_category(self, icecat_category, public_categories):
        """Find best matching website category for an Icecat category string."""
        normalized_target = self._normalize_category_text(icecat_category)
        if not normalized_target:
            return self.env['product.public.category']

        # 1) Exact name match (case-insensitive)
        exact = public_categories.filtered(
            lambda c: self._normalize_category_text(c.name) == normalized_target
        )
        if exact:
            return exact[:1]

        # 2) Exact display_name match (case-insensitive)
        exact_display = public_categories.filtered(
            lambda c: self._normalize_category_text(c.display_name) == normalized_target
        )
        if exact_display:
            return exact_display[:1]

        # 3) Fuzzy match on name + display_name
        best = self.env['product.public.category']
        best_score = 0.0
        for category in public_categories:
            name_score = SequenceMatcher(
                None,
                normalized_target,
                self._normalize_category_text(category.name),
            ).ratio()
            display_score = SequenceMatcher(
                None,
                normalized_target,
                self._normalize_category_text(category.display_name),
            ).ratio()
            score = max(name_score, display_score)
            if score > best_score:
                best_score = score
                best = category

        if best and best_score >= 0.78:
            return best

        return self.env['product.public.category']

    @api.model
    def _get_or_create_public_category_for_icecat(self, icecat_category, public_categories):
        """Resolve website category by best match, fallback to creating one."""
        category = self._find_best_public_category(icecat_category, public_categories)
        if category:
            return category

        # Fallback: create a clean top-level category with Icecat name
        clean_name = (icecat_category or '').strip()
        if not clean_name:
            return self.env['product.public.category']

        return self.env['product.public.category'].create({'name': clean_name})

    def action_restore_website_categories(self):
        """
        Restore website categories for mappings and linked products.

        Strategy:
        - Process mappings without website category
        - Resolve best matching product.public.category (exact/fuzzy)
        - Create category if no match exists
        - Reapply mapping to linked products
        """
        self.ensure_one()

        mappings_to_fix = self.search([('odoo_category_id', '=', False)])
        if not mappings_to_fix:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Nothing to restore'),
                    'message': _('All mappings already have a Website Category.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        public_categories = self.env['product.public.category'].search([])

        # Safety: if one mapped website category dominates, exclude it from
        # auto-match candidates to avoid restoring back into the same mistake.
        mapped_domain = [('odoo_category_id', '!=', False)]
        total_mapped = self.search_count(mapped_domain)
        if total_mapped:
            grouped = self.read_group(mapped_domain, ['odoo_category_id'], ['odoo_category_id'], lazy=False)
            grouped = [g for g in grouped if g.get('odoo_category_id')]
            if grouped:
                dominant = max(grouped, key=lambda g: g['odoo_category_id_count'])
                dominant_category_id = dominant['odoo_category_id'][0]
                dominant_count = dominant['odoo_category_id_count']
                if dominant_count >= int(total_mapped * 0.5):
                    public_categories = public_categories.filtered(lambda c: c.id != dominant_category_id)

        restored_mappings = 0
        created_categories = 0
        updated_products = 0

        for mapping in mappings_to_fix:
            category = self._get_or_create_public_category_for_icecat(
                mapping.icecat_category,
                public_categories,
            )
            if not category:
                continue

            # refresh cache if new category was created
            if category.id not in public_categories.ids:
                created_categories += 1
                public_categories |= category

            mapping.write({'odoo_category_id': category.id})
            restored_mappings += 1

            products = self.env['product.template'].search([
                ('icecat_category', '=', mapping.icecat_category)
            ])
            for product in products:
                vals = mapping._prepare_product_mapping_vals(product)
                if vals:
                    product.write(vals)
                    updated_products += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Category restore completed'),
                'message': _(
                    'Restored %(mappings)s mappings, created %(created)s categories, updated %(products)s products.'
                ) % {
                    'mappings': restored_mappings,
                    'created': created_categories,
                    'products': updated_products,
                },
                'type': 'success',
                'sticky': True,
            }
        }

    @api.model
    def _split_icecat_category_path(self, category_name):
        """Split Icecat category into hierarchy parts when possible."""
        raw = (category_name or '').strip()
        if not raw:
            return []

        if ' > ' in raw:
            parts = [part.strip() for part in raw.split('>') if part.strip()]
            if parts:
                return parts

        if ' / ' in raw:
            parts = [part.strip() for part in raw.split('/') if part.strip()]
            if parts:
                return parts

        return [raw]

    @api.model
    def _get_or_create_public_category_with_parent(self, name, parent=False):
        """Get or create product.public.category by name + parent."""
        domain = [('name', '=', name)]
        if parent:
            domain.append(('parent_id', '=', parent.id))
        else:
            domain.append(('parent_id', '=', False))

        category = self.env['product.public.category'].search(domain, limit=1)
        if category:
            return category

        values = {'name': name}
        if parent:
            values['parent_id'] = parent.id
        return self.env['product.public.category'].create(values)

    @api.model
    def _run_rebuild_website_category_structure(self):
        """
        Rebuild website category structure from Icecat categories.

        - Creates/uses root category 'Icecat (Rebuilt)'
        - Builds hierarchy from icecat_category text
        - Rewrites mapping website categories to rebuilt leaf nodes
        - Reapplies mappings to products
        """
        mappings = self.search([('icecat_category', '!=', False)])
        if not mappings:
            return {
                'rebuilt_mappings': 0,
                'created_categories': 0,
                'updated_products': 0,
                'status': 'no_data',
            }

        # Snapshot currently managed website categories so old/wrong mapped
        # categories are removed from products during rebuild.
        old_managed_category_ids = set(
            self.search([('odoo_category_id', '!=', False)]).mapped('odoo_category_id').ids
        )

        root = self._get_or_create_public_category_with_parent('Icecat (Rebuilt)', parent=False)

        rebuilt_mappings = 0
        created_categories = 0
        updated_products = 0

        for mapping in mappings:
            parts = self._split_icecat_category_path(mapping.icecat_category)
            if not parts:
                continue

            parent = root
            leaf = root
            for part in parts:
                existing = self.env['product.public.category'].search([
                    ('name', '=', part),
                    ('parent_id', '=', parent.id),
                ], limit=1)
                if existing:
                    leaf = existing
                else:
                    leaf = self.env['product.public.category'].create({
                        'name': part,
                        'parent_id': parent.id,
                    })
                    created_categories += 1
                parent = leaf

            mapping.with_context(icecat_allow_mass_category_write=True).write({'odoo_category_id': leaf.id})
            rebuilt_mappings += 1

            products = self.env['product.template'].search([
                ('icecat_category', '=', mapping.icecat_category)
            ])
            for product in products:
                vals = mapping._prepare_product_mapping_vals(product)
                if 'public_categ_ids' in product._fields:
                    current_ids = set(product.public_categ_ids.ids)
                    kept_ids = list(current_ids - old_managed_category_ids)
                    vals['public_categ_ids'] = [(6, 0, kept_ids + [leaf.id])]
                if vals:
                    product.write(vals)
                    updated_products += 1

        return {
            'rebuilt_mappings': rebuilt_mappings,
            'created_categories': created_categories,
            'updated_products': updated_products,
            'status': 'done',
        }

    def action_rebuild_website_category_structure(self):
        self.ensure_one()
        result = self._run_rebuild_website_category_structure()
        if result.get('status') == 'no_data':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Nothing to rebuild'),
                    'message': _('No Icecat category mappings found.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rebuild completed'),
                'message': _(
                    'Rebuilt %(mappings)s mappings, created %(categories)s categories, updated %(products)s products under "Icecat (Rebuilt)".'
                ) % {
                    'mappings': result.get('rebuilt_mappings', 0),
                    'categories': result.get('created_categories', 0),
                    'products': result.get('updated_products', 0),
                },
                'type': 'success',
                'sticky': True,
            }
        }

    @api.model
    def run_upgrade_category_recovery(self):
        """Run automatic recovery on module upgrade when anomaly is detected."""
        mappings = self.search([('icecat_category', '!=', False)])
        if not mappings:
            return True

        total_mapped = self.search_count([('odoo_category_id', '!=', False)])
        anomaly_detected = False
        if total_mapped:
            grouped = self.read_group(
                [('odoo_category_id', '!=', False)],
                ['odoo_category_id'],
                ['odoo_category_id'],
                lazy=False,
            )
            grouped = [g for g in grouped if g.get('odoo_category_id')]
            if grouped:
                dominant = max(grouped, key=lambda g: g['odoo_category_id_count'])
                if dominant['odoo_category_id_count'] >= int(total_mapped * 0.5):
                    anomaly_detected = True

        missing_count = self.search_count([
            ('icecat_category', '!=', False),
            ('odoo_category_id', '=', False),
        ])
        if missing_count:
            anomaly_detected = True

        if not anomaly_detected:
            return True

        self._run_rebuild_website_category_structure()
        return True

    def action_archive_unused_wrong_categories(self):
        """
        Archive likely wrong website categories when they are no longer used.

        Targets:
        - Explicit known wrong category names (e.g. Randapparatuur / Laders)
        - Previously dominant mapping category

        Safety:
        - Only archive when category is not used on any product
        - Only archive when category is not referenced by any mapping
        """
        self.ensure_one()

        category_model = self.env['product.public.category']
        product_model = self.env['product.template']

        candidates = category_model.browse()

        explicit_candidates = category_model.search([
            ('name', 'ilike', 'Randapparatuur / Laders')
        ])
        candidates |= explicit_candidates

        mapped_domain = [('odoo_category_id', '!=', False)]
        grouped = self.read_group(mapped_domain, ['odoo_category_id'], ['odoo_category_id'], lazy=False)
        grouped = [g for g in grouped if g.get('odoo_category_id')]
        if grouped:
            dominant = max(grouped, key=lambda g: g['odoo_category_id_count'])
            dominant_category = category_model.browse(dominant['odoo_category_id'][0])
            candidates |= dominant_category

        if not candidates:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No candidate categories'),
                    'message': _('No likely wrong website categories were found.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        archived = []
        skipped = []

        for category in candidates:
            products_using = product_model.search_count([('public_categ_ids', 'in', [category.id])])
            mappings_using = self.search_count([('odoo_category_id', '=', category.id)])

            if products_using == 0 and mappings_using == 0:
                if 'active' in category._fields:
                    category.write({'active': False})
                else:
                    new_name = category.name or ''
                    if not new_name.startswith('[ARCHIVED] '):
                        category.write({'name': '[ARCHIVED] %s' % new_name})
                archived.append(category.display_name)
            else:
                skipped.append('%s (products=%s, mappings=%s)' % (
                    category.display_name,
                    products_using,
                    mappings_using,
                ))

        if not archived:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Nothing archived'),
                    'message': _('All candidate categories are still in use: %s') % '; '.join(skipped[:5]),
                    'type': 'warning',
                    'sticky': True,
                }
            }

        message = _('Archived %s category/categorieën: %s') % (len(archived), ', '.join(archived[:8]))
        if skipped:
            message += _(' | Skipped in-use: %s') % '; '.join(skipped[:5])

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cleanup completed'),
                'message': message,
                'type': 'success',
                'sticky': True,
            }
        }
