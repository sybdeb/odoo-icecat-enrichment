# -*- coding: utf-8 -*-

import base64
import logging
import requests
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EnrichmentManager(models.AbstractModel):
    _name = 'enrichment.manager'
    _description = 'Product Enrichment Manager - Coördineert BarcodeLookup en Icecat'

    @api.model
    def _get_config_param(self, param_name, default=None):
        """Helper to get configuration parameters"""
        return self.env['ir.config_parameter'].sudo().get_param(
            f'product_content_verrijking.{param_name}',
            default=default
        )

    @api.model
    def _get_enabled_sources(self):
        """Get list of enabled enrichment sources in priority order"""
        sources = []
        
        # Check configured priority
        priority = self._get_config_param('source_priority', 'barcodelookup_first')
        
        barcodelookup_enabled = self._get_config_param('barcodelookup_enabled', 'False') == 'True'
        icecat_enabled = self._get_config_param('icecat_enabled', 'True') == 'True'
        
        if priority == 'barcodelookup_first':
            if barcodelookup_enabled:
                sources.append('barcodelookup')
            if icecat_enabled:
                sources.append('icecat')
        elif priority == 'icecat_first':
            if icecat_enabled:
                sources.append('icecat')
            if barcodelookup_enabled:
                sources.append('barcodelookup')
        elif priority == 'barcodelookup_only':
            if barcodelookup_enabled:
                sources.append('barcodelookup')
        elif priority == 'icecat_only':
            if icecat_enabled:
                sources.append('icecat')
        
        return sources

    @api.model
    def _fetch_from_source(self, source, barcode):
        """Fetch product data from a specific source"""
        if source == 'barcodelookup':
            connector = self.env['barcode.lookup.connector']
            return connector.fetch_product_data(barcode)
        elif source == 'icecat':
            connector = self.env['icecat.connector']
            return connector.fetch_product_data(barcode)
        else:
            return {'success': False, 'error': f'Unknown source: {source}'}

    @api.model
    def _get_field_mapping(self):
        """
        Get field mapping configuration
        Returns dict of field -> {'overwrite': bool, 'sources': [list]}
        """
        # Get all field mappings from database
        mappings = self.env['enrichment.field.mapping'].search([])
        
        field_config = {}
        for mapping in mappings:
            # Parse allowed sources
            allowed_sources = []
            if mapping.allow_barcodelookup:
                allowed_sources.append('barcodelookup')
            if mapping.allow_icecat:
                allowed_sources.append('icecat')
            
            field_config[mapping.field_name] = {
                'overwrite': mapping.allow_overwrite,
                'sources': allowed_sources,
            }
        
        # If no mappings configured, use defaults
        if not field_config:
            field_config = {
                'name': {'overwrite': False, 'sources': ['barcodelookup', 'icecat']},
                'description_sale': {'overwrite': True, 'sources': ['icecat']},  # Icecat is better
                'image_1920': {'overwrite': False, 'sources': ['barcodelookup', 'icecat']},
            }
        
        return field_config

    @api.model
    def _can_update_field(self, product, field_name, source, field_config):
        """
        Check if we can update a specific field based on configuration
        
        :param product: product.template record
        :param field_name: technical field name (e.g. 'name', 'description_sale')
        :param source: data source name ('barcodelookup' or 'icecat')
        :param field_config: field mapping configuration dict
        :return: Boolean
        """
        # Get config for this field
        config = field_config.get(field_name, {'overwrite': False, 'sources': []})
        
        # Check if this source is allowed for this field
        if source not in config['sources']:
            return False
        
        # Get current field value
        current_value = product[field_name]
        
        # If field is empty, always allow
        if not current_value:
            return True
        
        # If field has value, check overwrite setting
        return config['overwrite']

    @api.model
    def _download_image(self, image_url):
        """Download image from URL and return base64 encoded data"""
        try:
            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                return base64.b64encode(response.content)
            else:
                _logger.warning(f"Failed to download image: {image_url}")
                return None
        except Exception as e:
            _logger.error(f"Error downloading image {image_url}: {e}")
            return None

    @api.model
    def _build_specifications_html(self, specifications):
        """
        Build collapsible accordion HTML from specifications
        Returns tuple: (highlights_html, full_specs_html)
        """
        if not specifications:
            return None, None
        
        # Group specifications
        specs_by_group = {}
        for spec in specifications:
            group = spec.get('group', 'General')
            if group not in specs_by_group:
                specs_by_group[group] = []
            specs_by_group[group].append(spec)
        
        # Build highlights (top 5 key features)
        highlights_html = None
        try:
            highlight_candidates = []
            preferred_groups = [
                'Display', 'Performance', 'Processor', 'Graphics', 'Memory',
                'Storage', 'Ports & interfaces', 'Connectivity', 'Battery', 'Design'
            ]
            
            for pg in preferred_groups:
                for spec in specs_by_group.get(pg, []):
                    name = str(spec.get('name', '')).strip()
                    value = str(spec.get('value', '')).strip()
                    if not name or not value or len(value) > 60:
                        continue
                    
                    # Filter noise
                    blacklist = ['Certification', 'Harmonized System', 'EPREL', 'Compliance']
                    if any(b.lower() in name.lower() for b in blacklist):
                        continue
                    
                    highlight_candidates.append({'name': name, 'value': value})
                    if len(highlight_candidates) >= 5:
                        break
                
                if len(highlight_candidates) >= 5:
                    break
            
            if highlight_candidates:
                items_html = ''.join([
                    f"<li class='col'><strong>{h['name']}</strong>: {h['value']}</li>" 
                    for h in highlight_candidates
                ])
                highlights_html = (
                    "<div class='mt-3'><h3>Belangrijkste kenmerken</h3>"
                    "<ul class='list-unstyled row row-cols-1 row-cols-md-2 g-2'>"
                    f"{items_html}"
                    "</ul></div>"
                )
        except Exception as e:
            _logger.warning(f"Failed to build highlights: {e}")
        
        # Build full specifications accordion
        specs_html = '<div class="accordion mt-4" id="productSpecifications">'
        
        for idx, (group_name, specs) in enumerate(specs_by_group.items()):
            collapse_id = f"collapse{idx}"
            is_first = idx == 0
            show_class = "show" if is_first else ""
            collapsed_class = "" if is_first else "collapsed"
            
            specs_html += f'''
            <div class="accordion-item">
                <h2 class="accordion-header" id="heading{idx}">
                    <button class="accordion-button {collapsed_class}" type="button" data-bs-toggle="collapse" 
                            data-bs-target="#{collapse_id}" aria-expanded="{str(is_first).lower()}" aria-controls="{collapse_id}">
                        {group_name}
                    </button>
                </h2>
                <div id="{collapse_id}" class="accordion-collapse collapse {show_class}" 
                     aria-labelledby="heading{idx}" data-bs-parent="#productSpecifications">
                    <div class="accordion-body p-0">
                        <table class="table table-sm table-striped mb-0">
                            <tbody>
            '''
            
            for spec in specs:
                # DEBUG: Log spec structure
                _logger.info(f"Processing spec: {spec}")
                # Direct access like v18 - API returns exact 'name' and 'value' keys
                spec_name = spec.get('name', '')
                spec_value = spec.get('value', '')
                if spec_name and spec_value:
                    specs_html += f'<tr><td class="w-50">{spec_name}</td><td>{spec_value}</td></tr>'
                else:
                    _logger.warning(f"Skipping spec - name: '{spec_name}', value: '{spec_value}', full: {spec}")
            
            specs_html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            '''
        
        specs_html += '</div>'
        
        return highlights_html, specs_html

    @api.model
    def _apply_data_to_product(self, product, data, source):
        """
        Apply enrichment data to product based on field mapping configuration
        
        :param product: product.template record
        :param data: normalized data dict from connector
        :param source: source name ('barcodelookup' or 'icecat')
        :return: dict with applied fields
        """
        field_config = self._get_field_mapping()
        update_vals = {}
        ICP = self.env['ir.config_parameter'].sudo()
        
        # Product name
        if data.get('name'):
            if self._can_update_field(product, 'name', source, field_config):
                update_vals['name'] = data['name']
        
        # Description handling based on v18 toggles
        if source == 'icecat':
            description_parts = []
            
            # Sync description toggle (v18 compatibility)
            sync_description = ICP.get_param('product_content_verrijking.icecat_sync_description', 'False') == 'True'
            if sync_description and data.get('description'):
                if self._can_update_field(product, 'description_sale', source, field_config):
                    description_parts.append(data['description'])
            
            # Sync specifications to description toggle (v18 compatibility)
            sync_specs = ICP.get_param('product_content_verrijking.icecat_sync_specifications', 'True') == 'True'
            if sync_specs and data.get('specifications'):
                highlights_html, specs_html = self._build_specifications_html(data['specifications'])
                
                # Add highlights
                if highlights_html:
                    update_vals['enrichment_highlights_html'] = highlights_html
                
                # Add specs HTML to description if toggle enabled (v18 behavior)
                if specs_html:
                    description_parts.append(specs_html)
            
            # Combine description parts like v18
            if description_parts:
                combined_description = '\n\n'.join(description_parts)
                update_vals['description_sale'] = combined_description
                # Also set website_description (v18 behavior)
                update_vals['website_description'] = combined_description
        else:
            # Non-Icecat sources (BarcodeLookup)
            if data.get('description'):
                if self._can_update_field(product, 'description_sale', source, field_config):
                    update_vals['description_sale'] = data['description']
        
        # Image handling with toggle (v18 compatibility)
        sync_images = ICP.get_param('product_content_verrijking.icecat_sync_images', 'True') == 'True'
        if sync_images and data.get('image_url'):
            if self._can_update_field(product, 'image_1920', source, field_config):
                image_data = self._download_image(data['image_url'])
                if image_data:
                    update_vals['image_1920'] = image_data
        
        # Source tracking fields
        update_vals[f'enrichment_source_{source}'] = True
        update_vals[f'enrichment_source_{source}_id'] = data.get('source_id', '')
        
        # Icecat specific fields
        if source == 'icecat':
            update_vals['enrichment_icecat_brand'] = data.get('brand', '')
            update_vals['enrichment_icecat_category'] = data.get('category', '')
            update_vals['enrichment_icecat_quality'] = data.get('quality', '')
        
        # BarcodeLookup specific fields
        if source == 'barcodelookup':
            update_vals['enrichment_barcodelookup_brand'] = data.get('brand', '')
            update_vals['enrichment_barcodelookup_mpn'] = data.get('mpn', '')
        
        return update_vals

    @api.model
    def enrich_product(self, product, barcode=None):
        """
        Main method to enrich a product using configured sources
        
        Strategy:
        1. Get list of enabled sources in priority order
        2. For each source:
           a. Fetch data
           b. Apply data according to field mapping
           c. If all required fields filled, optionally stop
        3. Update sync status
        
        :param product: product.template record
        :param barcode: EAN/GTIN code (optional, will be retrieved from variants)
        :return: dict with success status and message
        """
        # Get barcode
        if not barcode:
            barcode = product.product_variant_ids.filtered(lambda v: v.barcode)[:1].barcode
        
        if not barcode:
            return {
                'success': False,
                'error': _('Product heeft geen barcode (EAN/GTIN)')
            }
        
        # Mark as pending
        product.write({'enrichment_status': 'pending'})
        
        # Get enabled sources in priority order
        sources = self._get_enabled_sources()
        
        if not sources:
            product.write({
                'enrichment_status': 'error',
                'enrichment_error_message': _('Geen enrichment bronnen geconfigureerd'),
                'enrichment_last_sync': fields.Datetime.now(),
            })
            return {
                'success': False,
                'error': _('Geen enrichment bronnen geconfigureerd')
            }
        
        _logger.info(f"Enriching product {product.id} with sources: {sources}")
        
        all_updates = {}
        successful_sources = []
        errors = []
        
        # Try each source in order
        for source in sources:
            _logger.info(f"Trying source: {source}")
            
            result = self._fetch_from_source(source, barcode)
            
            if result.get('success'):
                data = result.get('data', {})
                updates = self._apply_data_to_product(product, data, source)
                
                # Merge updates (later sources can overwrite if allowed)
                all_updates.update(updates)
                successful_sources.append(source)
                
                _logger.info(f"Successfully fetched data from {source}")
            else:
                error_msg = result.get('error', 'Unknown error')
                errors.append(f"{source}: {error_msg}")
                _logger.warning(f"Failed to fetch from {source}: {error_msg}")
        
        # Check if we got any data
        if not successful_sources:
            product.write({
                'enrichment_status': 'no_data',
                'enrichment_error_message': '\n'.join(errors),
                'enrichment_last_sync': fields.Datetime.now(),
            })
            return {
                'success': False,
                'error': _('Geen data gevonden in geconfigureerde bronnen:\n%s') % '\n'.join(errors)
            }
        
        # Apply all updates
        all_updates.update({
            'enrichment_status': 'synced',
            'enrichment_last_sync': fields.Datetime.now(),
            'enrichment_error_message': False,
            'enrichment_sources_used': ', '.join(successful_sources),
        })
        
        product.write(all_updates)
        
        _logger.info(f"Successfully enriched product {product.id} using sources: {successful_sources}")
        
        return {
            'success': True,
            'message': _('Product verrijkt met data van: %s') % ', '.join(successful_sources),
            'sources': successful_sources
        }
