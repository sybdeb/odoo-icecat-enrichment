# -*- coding: utf-8 -*-
{
    'name': 'Icecat Product Enrichment',
    'version': '19.0.1.0.0',
    'category': 'Sales/Product',
    'summary': 'Verrijk producten met Icecat data op basis van EAN/GTIN',
    'description': """
Icecat Product Enrichment
==========================
Deze module integreert met Icecat JSON API om automatisch product data te verrijken.

Features:
---------
* Configureer Icecat credentials in Website Settings
* Automatische batch synchronisatie voor nieuwe producten
* Geplande updates voor bestaande producten
* Ondersteuning voor Icecat Open Catalog en Full Catalog
* Track sync status per product
* Handmatige sync acties

Batch Processing:
-----------------
* Nieuwe producten: 10 producten per batch
* Updates: Grotere batches voor nachtelijke verwerking
    """,
    'author': 'Nerbys',
    'website': 'https://www.nerbys.nl',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'wizards/icecat_sync_wizard_views.xml',
        'wizards/spec_manager_wizard_views.xml',
        'views/product_template_views.xml',
        'views/icecat_sync_log_views.xml',
        'views/icecat_category_mapping_views.xml',
        'views/product_website_views.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
