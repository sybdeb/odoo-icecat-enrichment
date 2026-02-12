# -*- coding: utf-8 -*-

import base64
import logging
import requests
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IcecatConnector(models.AbstractModel):
    _name = 'icecat.connector'
    _description = 'Icecat API Connector'

    @api.model
    def _get_config_param(self, param_name, default=None):
        """Helper to get configuration parameters"""
        return self.env['ir.config_parameter'].sudo().get_param(
            f'product_content_verrijking.{param_name}',
            default=default
        )

    @api.model
    def _cfg_bool(self, key, default=False):
        """Veilige boolean uit ir.config_parameter"""
        val = self._get_config_param(key)
        return str(val).lower() in ('true', '1', 'yes', 'on')

    @api.model
    def _cfg_int(self, key, default=0):
        val = self._get_config_param(key)
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    @api.model
    def _get_api_credentials(self):
        """Get Icecat API credentials from settings"""
        username = self._get_config_param('username')
        password = self._get_config_param('password')
        
        if not username or not password:
            raise UserError(_(
                'Icecat credentials not configured. '
                'Please configure them in Website Settings > Icecat Configuration.'
            ))
        
        return username, password

    @api.model
    def _get_api_url(self):
        """Get Icecat API base URL"""
        return self._get_config_param('api_url', 'https://live.icecat.biz/api')

    @api.model
    def _make_api_request(self, ean_code):
        """
        Make a request to Icecat JSON API
        Based on: https://iceclog.com/manual-for-icecat-json-product-requests/
        """
        username, password = self._get_api_credentials()
        api_url = self._get_api_url()
        
        # Ensure EAN code is a string
        ean_code = str(ean_code or '').strip()
        
        # Log the barcode we received
        _logger.info(f"Received EAN code: '{ean_code}' (type: {type(ean_code).__name__})")
        
        # Ensure EAN code is not empty
        if not ean_code:
            _logger.error("EAN code is empty!")
            return {'success': False, 'error': 'EAN code is empty'}
        
        # Construct the API endpoint for EAN lookup
        # Format: https://live.icecat.biz/api?lang=EN&shopname=username&GTIN=EAN&content=
        # Get language from context or use Dutch as default
        lang_code = self.env.context.get('lang', 'nl_NL')
        # Map Odoo language codes to Icecat language codes
        icecat_lang = 'nl' if lang_code.startswith('nl') else 'en'
        url = f"{api_url}?lang={icecat_lang}&shopname={username}&GTIN={ean_code}&content="
        
        _logger.info(f"Requesting Icecat data for EAN: {ean_code}")
        
        try:
            # Basic authentication
            auth_string = f"{username}:{password}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Accept': 'application/json',
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            # Log response status and URL
            _logger.info(f"Icecat API URL: {url}")
            _logger.info(f"Icecat API response status: {response.status_code}")
            if response.status_code != 200:
                _logger.error(f"Icecat API response body: {response.text[:500]}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    return {'success': True, 'data': data}
                except ValueError as e:
                    _logger.error(f"Failed to parse JSON response: {e}")
                    return {
                        'success': False,
                        'error': _('Invalid JSON response from Icecat API')
                    }
            elif response.status_code == 404:
                # Check if it's a brand restriction vs product not found
                try:
                    error_data = response.json()
                    if 'brand restrictions' in error_data.get('Message', '').lower():
                        return {
                            'success': False,
                            'error': _('Product has brand restrictions. This product requires Full Icecat subscription.'),
                            'status': 'no_data'
                        }
                except:
                    pass
                return {
                    'success': False,
                    'error': _('Product not found in Icecat database'),
                    'status': 'no_data'
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': _('Authentication failed. Please check your Icecat credentials.')
                }
            else:
                error_msg = f"Icecat API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('message', '')}"
                except:
                    error_msg += f" - {response.text[:200]}"
                
                _logger.error(error_msg)
                return {'success': False, 'error': error_msg}
                
        except requests.exceptions.Timeout:
            error_msg = _('Icecat API request timed out')
            _logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except requests.exceptions.ConnectionError:
            error_msg = _('Failed to connect to Icecat API')
            _logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            _logger.exception(error_msg)
            return {'success': False, 'error': error_msg}

    @api.model
    def _parse_product_data(self, icecat_data):
        """Parse Icecat JSON response and extract product information"""
        try:
            # Navigate the JSON structure
            if 'data' not in icecat_data:
                return None
            
            data = icecat_data['data']
            
            # Extract general info
            general_info = data.get('GeneralInfo', {})
            
            # Extract category name from the Category object
            category_obj = general_info.get('Category', {})
            category_name = ''
            if isinstance(category_obj, dict):
                # Category is like {'CategoryID': '222', 'Name': {'Value': 'Computer Monitors', 'Language': 'EN'}}
                name_obj = category_obj.get('Name', {})
                if isinstance(name_obj, dict):
                    category_name = name_obj.get('Value', '')
                else:
                    category_name = str(category_obj.get('Name', ''))
            elif isinstance(category_obj, str):
                category_name = category_obj
            
            product_info = {
                'product_id': general_info.get('IcecatId'),
                'title': general_info.get('Title', ''),
                'brand': general_info.get('Brand', ''),
                'category': category_name,
                'quality': general_info.get('Quality', ''),
                'description_short': general_info.get('Description', {}).get('ShortDesc', ''),
                'description_long': general_info.get('Description', {}).get('LongDesc', ''),
                'images': [],
                'specifications': []
            }
            
            # Extract images
            gallery = data.get('Gallery', [])
            for image in gallery:
                if image.get('Pic'):
                    product_info['images'].append({
                        'url': image.get('Pic'),
                        'size': image.get('Size', 0),
                        'type': image.get('Type', 'product')
                    })
            
            # Extract specifications
            feature_groups = data.get('FeaturesGroups', [])
            for group in feature_groups:
                group_name = group.get('FeatureGroup', {}).get('Name', {}).get('Value', '')
                features = group.get('Features', [])
                
                for feature in features:
                    feature_obj = feature.get('Feature', {})
                    spec_name = feature_obj.get('Name', {}).get('Value', '')
                    spec_value = feature.get('Value', '')
                    
                    if spec_name and spec_value:
                        product_info['specifications'].append({
                            'group': group_name,
                            'name': spec_name,
                            'value': spec_value
                        })
            
            return product_info
            
        except Exception as e:
            _logger.error(f"Error parsing Icecat data: {e}")
            return None

    @api.model
    def _download_image(self, image_url):
        """Download image from URL and return base64 encoded data"""
        try:
            response = requests.get(
                image_url,
                stream=True,
                timeout=15,
                headers={'User-Agent': 'Odoo/18.0 Icecat-Module'},
            )
            response.raise_for_status()
            return base64.b64encode(response.content)
        except Exception as e:
            _logger.warning("Image download mislukt %s: %s", image_url, e)
            return None

    @api.model
    def _get_or_create_attribute_category(self, category_name):
        """
        Get or create a product attribute category for grouping
        Returns: product.attribute.category record
        """
        CategoryModel = self.env['product.attribute.category']
        
        # Search for existing category
        category = CategoryModel.search([
            ('name', '=', category_name),
        ], limit=1)
        
        if not category:
            # Create new category with sequence based on common order
            sequence_map = {
                'Design': 10,
                'Beeldscherm': 20,
                'Processor': 30,
                'Geheugen': 40,
                'Opslagmedia': 50,
                'Grafisch': 60,
                'Audio': 70,
                'Camera': 80,
                'Netwerk': 90,
                'Poorten & interfaces': 100,
                'Toetsenbord': 110,
                'Software': 120,
                'Accu/Batterij': 130,
                'Energie': 140,
                'Beveiliging': 150,
                'Gewicht en omvang': 160,
                'Inhoud van de verpakking': 170,
            }
            sequence = sequence_map.get(category_name, 999)
            
            category = CategoryModel.create({
                'name': category_name,
                'sequence': sequence,
            })
            _logger.info(f"Created new attribute category: {category.name}")
        
        return category

    @api.model
    def _detect_attribute_display_type(self, spec_name, spec_values):
        """
        Detect the best display type for an attribute based on name and values
        Returns: 'select', 'radio', 'color', 'pills', or 'multi'
        """
        spec_name_lower = spec_name.lower()
        
        # Color detection
        if 'kleur' in spec_name_lower or 'color' in spec_name_lower or 'colour' in spec_name_lower:
            return 'color'
        
        # Boolean/Yes-No detection (radio buttons)
        unique_values = set(str(v).strip().upper() for v in spec_values if v)
        if unique_values.issubset({'Y', 'N', 'YES', 'NO', 'JA', 'NEE', 'TRUE', 'FALSE', '1', '0'}):
            return 'radio'
        
        # If 2-3 unique values, use pills for compact display
        if len(unique_values) <= 3:
            return 'pills'
        
        # Default: select dropdown for many options
        return 'select'

    @api.model
    def _sync_product_attributes(self, product, specifications):
        """
        Sync Icecat specifications to Odoo's standard product.attribute system
        Each specification becomes an individual attribute (e.g., "Kleur", "Processorfabrikant")
        Grouped by category for better organization on website and backend
        100% compatible with eCommerce filters, variants, and search
        """
        if not specifications:
            return
        
        attribute_obj = self.env['product.attribute']
        value_obj = self.env['product.attribute.value']
        template_attr_obj = self.env['product.template.attribute.line']
        
        _logger.info(f"Syncing {len(specifications)} specifications as individual attributes for product {product.name}")
        
        # Remove only Icecat-managed attributes (preserve manual ones)
        icecat_lines = product.attribute_line_ids.filtered(
            lambda l: (
                l.attribute_id.name.startswith('[Icecat]') or 
                (l.attribute_id.category_id and l.attribute_id.category_id.name.startswith('[Icecat]'))
            )
        )
        if icecat_lines:
            _logger.info(f"Removing {len(icecat_lines)} existing Icecat attribute lines")
            icecat_lines.unlink()
        
        # Group specifications by category
        grouped_specs = {}
        for spec in specifications:
            group = spec.get('group') or 'Algemeen'
            if group not in grouped_specs:
                grouped_specs[group] = []
            grouped_specs[group].append(spec)
        
        _logger.info(f"Processing {len(grouped_specs)} specification groups: {list(grouped_specs.keys())}")
        
        # Process each specification group
        for group_name, specs in grouped_specs.items():
            # Get or create category for this group
            category = self._get_or_create_attribute_category(group_name)
            
            # Create individual attribute for EACH specification
            for spec in specs:
                spec_name = spec.get('name')
                spec_value = str(spec.get('value', '')).strip()
                spec_unit = spec.get('unit', '').strip()
                
                if not spec_name or not spec_value:
                    continue
                
                # Add unit to value if present
                if spec_unit:
                    full_value = f"{spec_value} {spec_unit}"
                else:
                    full_value = spec_value
                
                # Find or create the attribute for this specific spec
                # Use spec name without [Icecat] prefix for cleaner display
                attribute = attribute_obj.search([
                    ('name', '=', spec_name),
                    ('category_id', '=', category.id)
                ], limit=1)
                
                if not attribute:
                    # Detect best display type
                    display_type = self._detect_attribute_display_type(spec_name, [spec_value])
                    
                    attribute = attribute_obj.create({
                        'name': spec_name,
                        'category_id': category.id,
                        'display_type': display_type,
                        'create_variant': 'no_variant',  # Don't create product variants
                    })
                    _logger.debug(f"Created attribute: {spec_name} ({display_type}) in {category.name}")
                
                # Find or create the attribute value
                value = value_obj.search([
                    ('attribute_id', '=', attribute.id),
                    ('name', '=', full_value)
                ], limit=1)
                
                if not value:
                    # For color attributes, try to set HTML color if value looks like a color
                    value_data = {
                        'attribute_id': attribute.id,
                        'name': full_value,
                    }
                    
                    # Simple color detection for common color names
                    if attribute.display_type == 'color':
                        color_map = {
                            'black': '#000000',
                            'white': '#FFFFFF',
                            'silver': '#C0C0C0',
                            'grey': '#808080',
                            'gray': '#808080',
                            'red': '#FF0000',
                            'blue': '#0000FF',
                            'green': '#00FF00',
                            'yellow': '#FFFF00',
                        }
                        color_name = full_value.lower().strip()
                        if color_name in color_map:
                            value_data['html_color'] = color_map[color_name]
                    
                    value = value_obj.create(value_data)
                    _logger.debug(f"Created value: {full_value} for {spec_name}")
                
                # Create or update attribute line for this product
                existing_line = product.attribute_line_ids.filtered(
                    lambda l: l.attribute_id.id == attribute.id
                )
                
                if existing_line:
                    # Add value if not already present
                    if value.id not in existing_line.value_ids.ids:
                        existing_line.write({
                            'value_ids': [(4, value.id)]
                        })
                else:
                    # Create new attribute line
                    template_attr_obj.create({
                        'product_tmpl_id': product.id,
                        'attribute_id': attribute.id,
                        'value_ids': [(6, 0, [value.id])]
                    })
        
        _logger.info(f"Successfully synced {len(specifications)} specifications to product attributes")


    @api.model
    def sync_product(self, product, barcode=None):
        """
        Main method to sync a single product with Icecat
        
        :param product: product.template record
        :param barcode: EAN/GTIN code to use (optional, will be retrieved from variants if not provided)
        :return: dict with success status and message
        """
        # Get barcode from parameter or from product variants
        if not barcode:
            barcode = product.product_variant_ids.filtered(lambda v: v.barcode)[:1].barcode
        
        if not barcode:
            return {
                'success': False,
                'error': _('Product has no barcode (EAN/GTIN)')
            }
        
        # Mark as pending
        product.write({'icecat_sync_status': 'pending'})
        
        # Make API request
        api_result = self._make_api_request(barcode)
        
        if not api_result.get('success'):
            # Update product with error status
            product.write({
                'icecat_sync_status': api_result.get('status', 'error'),
                'icecat_error_message': api_result.get('error', ''),
                'icecat_last_sync': fields.Datetime.now(),
            })
            return api_result
        
        # Parse the data
        product_info = self._parse_product_data(api_result['data'])
        
        if not product_info:
            product.write({
                'icecat_sync_status': 'error',
                'icecat_error_message': _('Failed to parse Icecat data'),
                'icecat_last_sync': fields.Datetime.now(),
            })
            return {
                'success': False,
                'error': _('Failed to parse Icecat data')
            }
        
        # Update product with Icecat data
        update_vals = {
            'icecat_sync_status': 'synced',
            'icecat_last_sync': fields.Datetime.now(),
            'icecat_brand': product_info.get('brand'),
            'icecat_category': product_info.get('category'),
            'icecat_error_message': False,
        }
        
        # Update name if empty
        # Always update product name with brand + title from Icecat
        if product_info.get('title'):
            brand = product_info.get('brand', '')
            title = product_info.get('title', '')
            if brand and title:
                update_vals['name'] = f"{brand} {title}"
            else:
                update_vals['name'] = title
        
        # Always update description_ecommerce for website display
        if product_info.get('description_long'):
            update_vals['description_ecommerce'] = product_info['description_long']
        elif product_info.get('description_short'):
            update_vals['description_ecommerce'] = product_info['description_short']
        
        # Update description_sale if configured
        if self._get_config_param('sync_description', 'True') == 'True':
            if product_info.get('description_long'):
                update_vals['description_sale'] = product_info['description_long']
            elif product_info.get('description_short'):
                update_vals['description_sale'] = product_info['description_short']
        
        # Update brand if product_brand module is installed
        if 'product_brand_id' in self.env['product.template']._fields:
            brand_name = product_info.get('brand')
            if brand_name:
                brand = self.env['product.brand'].search([('name', '=', brand_name)], limit=1)
                if not brand:
                    brand = self.env['product.brand'].create({'name': brand_name})
                update_vals['product_brand_id'] = brand.id

        # Update images if configured
        if self._get_config_param('sync_images', 'True') == 'True':
            if product_info.get('images'):
                # Get existing Icecat images (by name pattern)
                existing_images = self.env['product.image'].search([
                    ('product_tmpl_id', '=', product.id),
                    ('name', 'ilike', 'Icecat Image')
                ])
                # Delete old Icecat images to avoid duplicates
                existing_images.unlink()
                
                # Sync images
                image_count = 0
                for idx, image_info in enumerate(product_info['images']):
                    url = image_info.get('url') or image_info.get('pic')
                    if not url:
                        continue

                    image_data = self._download_image(url)
                    if not image_data:
                        continue

                    if idx == 0:
                        # Main image
                        update_vals['image_1920'] = image_data
                        image_count += 1
                    else:
                        # Extra images
                        self.env['product.image'].create({
                            'product_tmpl_id': product.id,
                            'image_1920': image_data,
                            'name': image_info.get('title', f"Icecat Image {idx + 1}"),
                            'sequence': idx,
                        })
                        image_count += 1

        
        # Write updates to product
        product.write(update_vals)
        
        # ALWAYS store raw specifications as JSON (source of truth)
        if product_info.get('specifications'):
            product.write({'icecat_specifications_raw': product_info['specifications']})
            
            # Convert JSON specs to Odoo attributes for website display & filtering
            self._sync_product_attributes(product, product_info['specifications'])
            _logger.info(f"Stored JSON and synced {len(product_info['specifications'])} specifications as Odoo attributes")
        
        # Apply category mapping if we have an Icecat category
        if product_info.get('category'):
            category_mapping = self.env['icecat.category.mapping'].apply_mapping(
                product, 
                product_info['category']
            )
            if category_mapping:
                product.write(category_mapping)
        
        _logger.info(f"Successfully synced product {product.id} with Icecat")
        
        return {
            'success': True,
            'message': _('Product successfully synced with Icecat'),
            'product_info': product_info
        }
