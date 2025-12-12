# -*- coding: utf-8 -*-

import logging
import requests
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BarcodeLookupConnector(models.AbstractModel):
    _name = 'barcode.lookup.connector'
    _description = 'BarcodeLookup.com API Connector'

    @api.model
    def _get_config_param(self, param_name, default=None):
        """Helper to get configuration parameters"""
        return self.env['ir.config_parameter'].sudo().get_param(
            f'product_content_verrijking.barcode_lookup_{param_name}',
            default=default
        )

    @api.model
    def _get_api_credentials(self):
        """Get BarcodeLookup API credentials from settings"""
        api_key = self._get_config_param('api_key')
        
        if not api_key:
            raise UserError(_(
                'BarcodeLookup API key niet geconfigureerd. '
                'Configureer deze in Website Settings > Product Verrijking.'
            ))
        
        return api_key

    @api.model
    def _get_api_url(self):
        """Get BarcodeLookup API base URL"""
        return 'https://api.barcodelookup.com/v3/products'

    @api.model
    def _make_api_request(self, barcode):
        """
        Make a request to BarcodeLookup API
        Documentation: https://www.barcodelookup.com/api
        """
        api_key = self._get_api_credentials()
        api_url = self._get_api_url()
        
        _logger.info(f"Requesting BarcodeLookup data for barcode: {barcode}")
        
        if not barcode:
            _logger.error("Barcode is empty!")
            return {'success': False, 'error': 'Barcode is empty'}
        
        try:
            params = {
                'barcode': barcode,
                'formatted': 'y',
                'key': api_key
            }
            
            response = requests.get(api_url, params=params, timeout=30)
            
            _logger.info(f"BarcodeLookup API response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check if products found
                    if data.get('products') and len(data['products']) > 0:
                        return {'success': True, 'data': data['products'][0]}
                    else:
                        return {
                            'success': False,
                            'error': _('Geen product gevonden in BarcodeLookup')
                        }
                        
                except ValueError as e:
                    _logger.error(f"Failed to parse JSON response: {e}")
                    return {
                        'success': False,
                        'error': _('Ongeldige JSON response van BarcodeLookup API')
                    }
                    
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': _('Product niet gevonden in BarcodeLookup database')
                }
                
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': _('Ongeldige BarcodeLookup API key')
                }
                
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                _logger.error(f"BarcodeLookup API error: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except requests.exceptions.Timeout:
            error_msg = _('BarcodeLookup API timeout (>30s)')
            _logger.error(error_msg)
            return {'success': False, 'error': error_msg}
            
        except requests.exceptions.RequestException as e:
            error_msg = _('BarcodeLookup API connection error: %s') % str(e)
            _logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    @api.model
    def _extract_product_data(self, api_data):
        """
        Extract and normalize product data from BarcodeLookup response
        
        BarcodeLookup API fields:
        - barcode_number
        - barcode_type
        - barcode_formats
        - mpn (Manufacturer Part Number)
        - model
        - asin
        - product_name / title
        - category
        - manufacturer
        - brand
        - contributors (author, artist, etc)
        - age_group
        - ingredients
        - nutrition_facts
        - color
        - gender
        - material
        - pattern
        - format
        - multipack
        - size
        - length, width, height, weight
        - release_date
        - description
        - features (array)
        - images (array)
        - stores (array with prices)
        - reviews (array)
        """
        if not api_data:
            return {}
        
        data = {
            'source': 'barcodelookup',
            'source_id': api_data.get('barcode_number', ''),
            'name': api_data.get('title') or api_data.get('product_name', ''),
            'brand': api_data.get('brand') or api_data.get('manufacturer', ''),
            'mpn': api_data.get('mpn', ''),
            'description': api_data.get('description', ''),
            'category': api_data.get('category', ''),
            'images': api_data.get('images', []),
            'features': api_data.get('features', []),
        }
        
        # Extract first image URL if available
        if data['images'] and len(data['images']) > 0:
            data['image_url'] = data['images'][0]
        
        # Note: We krijgen wel prijzen van stores, maar die gebruiken we NIET
        # omdat prijs uit een andere module komt
        
        _logger.info(f"Extracted BarcodeLookup data: name={data.get('name')}, brand={data.get('brand')}")
        
        return data

    @api.model
    def fetch_product_data(self, barcode):
        """
        Main method to fetch and extract product data from BarcodeLookup
        Returns dict with 'success' boolean and either 'data' or 'error'
        """
        result = self._make_api_request(barcode)
        
        if result.get('success'):
            extracted_data = self._extract_product_data(result.get('data'))
            return {
                'success': True,
                'data': extracted_data
            }
        else:
            return result
