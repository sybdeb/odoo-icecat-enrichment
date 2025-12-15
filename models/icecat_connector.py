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
    def _sync_product_attributes(self, product, specifications):
        """
        Sync Icecat specifications to Odoo's standard product.attribute system
        Groups specs by category with [Icecat] prefix for automatic backend grouping
        100% compatible with eCommerce filters, variants, and search
        """
        if not specifications:
            return
        
        attribute_obj = self.env['product.attribute']
        value_obj = self.env['product.attribute.value']
        template_attr_obj = self.env['product.template.attribute.line']
        
        _logger.info(f"Syncing {len(specifications)} specifications as attributes for product {product.name}")
        
        # Remove only Icecat-managed attributes (preserve manual ones)
        icecat_lines = product.attribute_line_ids.filtered(
            lambda l: l.attribute_id.name.startswith('[Icecat]')
        )
        if icecat_lines:
            icecat_lines.unlink()
        
        # Group specifications by category for cleaner attribute structure
        grouped_specs = {}
        for spec in specifications:
            group = spec.get('group') or 'Algemeen'
            if group not in grouped_specs:
                grouped_specs[group] = []
            grouped_specs[group].append(spec)
        
        # Create attributes per group (enables automatic backend grouping)
        for group_name, specs in grouped_specs.items():
            # Attribute name: [Icecat] Group → auto-groups in backend
            attr_name = f"[Icecat] {group_name}"
            
            # Find or create the group attribute
            attribute = attribute_obj.search([('name', '=', attr_name)], limit=1)
            if not attribute:
                attribute = attribute_obj.create({
                    'name': attr_name,
                    'display_type': 'select',
                    'create_variant': 'no_variant',  # Don't create product variants
                })
            
            # Collect all values for this group
            values_to_create = []
            for spec in specs:
                spec_name = spec.get('name')
                spec_value = str(spec.get('value', ''))
                
                if not spec_name or not spec_value:
                    continue
                
                # Value format: "Spec Name: Value"
                value_name = f"{spec_name}: {spec_value}"
                
                # Find or create the attribute value
                value = value_obj.search([
                    ('attribute_id', '=', attribute.id),
                    ('name', '=', value_name)
                ], limit=1)
                
                if not value:
                    value = value_obj.create({
                        'attribute_id': attribute.id,
                        'name': value_name,
                    })
                
                values_to_create.append(value.id)
            
            # Create attribute line with all values for this group
            if values_to_create:
                existing_line = product.attribute_line_ids.filtered(
                    lambda l: l.attribute_id.id == attribute.id
                )
                if not existing_line:
                    template_attr_obj.create({
                        'product_tmpl_id': product.id,
                        'attribute_id': attribute.id,
                        'value_ids': [(6, 0, values_to_create)]
                    })


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

                    # Optimize image size for webshop (max 2000x2000px)
                    try:
                        import io
                        from PIL import Image
                        img = Image.open(io.BytesIO(base64.b64decode(image_data)))
                        width, height = img.size
                        
                        # Maximum dimension for webshop images
                        MAX_DIMENSION = 2000
                        
                        if width > MAX_DIMENSION or height > MAX_DIMENSION:
                            _logger.info(f"Resizing image from {width}x{height} to max {MAX_DIMENSION}px")
                            
                            # Calculate new dimensions maintaining aspect ratio
                            if width > height:
                                new_width = MAX_DIMENSION
                                new_height = int(height * (MAX_DIMENSION / width))
                            else:
                                new_height = MAX_DIMENSION
                                new_width = int(width * (MAX_DIMENSION / height))
                            
                            # Convert to RGB if needed (some formats like CMYK cause issues)
                            if img.mode not in ('RGB', 'L'):
                                img = img.convert('RGB')
                            
                            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            
                            # Save optimized image
                            buffer = io.BytesIO()
                            img.save(buffer, format='JPEG', quality=85, optimize=True)
                            image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                            _logger.info(f"Resized to {new_width}x{new_height} (quality: 85)")
                        else:
                            _logger.info(f"Image size OK: {width}x{height}")
                    except Exception as e:
                        _logger.warning(f"Could not optimize image: {e}. Skipping this image.")
                        # Skip this image if resize fails
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
        
        # Store raw specifications for management
        if product_info.get('specifications'):
            product.write({'icecat_specifications_raw': product_info['specifications']})
        
        # Sync specifications as product attributes if configured
        if self._get_config_param('sync_attributes', 'False') == 'True':
            if product_info.get('specifications'):
                self._sync_product_attributes(product, product_info['specifications'])
        
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
