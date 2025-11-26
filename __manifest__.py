# -*- coding: utf-8 -*-
{
    'name': 'Icecat Product Enrichment',
    'version': '18.0.1.0.0',
    'category': 'Sales/Product',
    'summary': 'Enrich products with Icecat data based on EAN/GTIN',
    'description': """
Icecat Product Enrichment
==========================
This module integrates with Icecat JSON API to automatically enrich product data.

Features:
---------
* Configure Icecat credentials in Website Settings
* Automatic batch synchronization for new products
* Scheduled updates for existing products
* Support for Icecat Open Catalog and Full Catalog
* Track sync status per product
* Manual sync actions

Batch Processing:
-----------------
* New products: 10 products per batch, can run during the day
* Updates: Larger batches for night-time processing
    """,
    'author': 'Nerbys',
    'website': 'https://www.nerbys.nl',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'website_sale',
        'product_google_category',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/product_template_views.xml',
        'views/icecat_sync_log_views.xml',
        'views/icecat_category_mapping_views.xml',
        'views/website_product_specifications.xml',
        'wizards/icecat_sync_wizard_views.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
