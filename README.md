# Icecat Product Enrichment for Odoo 18

Automatisch producten verrijken met Icecat data op basis van EAN/GTIN codes.

## Features

✅ **Automatische synchronisatie**
- Nieuwe producten: Batches van 10 stuks per uur (overdag)
- Update bestaande producten: Grotere batches 's nachts om 02:00 uur
- Producten ouder dan 30 dagen worden automatisch bijgewerkt

✅ **Volledige configuratie via Website Settings**
- Icecat gebruikersnaam en wachtwoord
- Keuze tussen Open Catalog (gratis) en Full Catalog (betaald)
- Configureerbare batch groottes
- In-/uitschakelen van auto-sync

✅ **Flexibele data synchronisatie**
- Product beschrijvingen
- Product afbeeldingen
- Technische specificaties
- Merk en categorie informatie

✅ **Status tracking**
- Per product sync status bekijken
- Filters op sync status
- Foutmeldingen logging
- Laatste sync datum

✅ **Handmatige controle**
- Handmatige sync per product
- Bulk sync wizard voor meerdere producten
- Verschillende sync opties (niet gesynchroniseerd, fouten, verouderd, etc.)

## Installatie

1. Plaats de module in je `addons` folder
2. Update de app lijst in Odoo
3. Installeer "Icecat Product Enrichment"
4. Configureer je Icecat credentials in Website > Configuration > Settings

## Configuratie

Ga naar **Website > Configuration > Settings** en scroll naar **Icecat Configuration**:

1. **API Credentials**
   - Vul je Icecat gebruikersnaam in
   - Vul je Icecat wachtwoord in
   - Kies je catalog type (Open of Full)

2. **Synchronization Settings**
   - ✅ Sync Description: Product beschrijvingen bijwerken
   - ✅ Sync Images: Product afbeeldingen downloaden
   - ✅ Sync Specifications: Technische specs toevoegen

3. **Batch Processing**
   - New Products Batch Size: 10 (aanbevolen voor overdag)
   - Update Batch Size: 100 (aanbevolen voor 's nachts)

## Gebruik

### Automatische synchronisatie

De module synchroniseert automatisch:
- **Elk uur (overdag)**: 10 nieuwe producten met een EAN maar nog niet gesynchroniseerd
- **Elke nacht om 02:00**: 100 producten die langer dan 30 dagen geleden gesynchroniseerd zijn

### Handmatige synchronisatie

**Enkel product:**
1. Open een product
2. Zorg dat het product een barcode (EAN/GTIN) heeft
3. Klik op "Sync with Icecat" knop

**Meerdere producten:**
1. Ga naar Sales > Products > Products
2. Selecteer de producten die je wilt synchroniseren
3. Klik op Action > Sync with Icecat
4. Kies je sync type en batch size
5. Klik op "Start Sync"

### Filters gebruiken

In de product lijst zijn handige filters beschikbaar:
- **Not Synced with Icecat**: Producten die nog nooit gesynchroniseerd zijn
- **Synced with Icecat**: Succesvol gesynchroniseerde producten
- **Icecat Sync Errors**: Producten waarbij de sync fout ging
- **Pending Icecat Sync**: Producten in de wachtrij

## Icecat Account Informatie

Deze module werkt met de Icecat JSON API zoals beschreven op:
https://iceclog.com/manual-for-icecat-json-product-requests/

### Vereisten:
- Een Icecat account (gratis voor Open Catalog)
- Geldige gebruikersnaam en wachtwoord
- Internet connectie

### Icecat Open vs Full:
- **Open Catalog**: Gratis, beperkte data, basis product info
- **Full Catalog**: Betaald, volledige data, uitgebreide specs en afbeeldingen

## Technische Details

### Velden toegevoegd aan product.template:

- `icecat_sync_status`: Status van de synchronisatie
- `icecat_last_sync`: Datum/tijd van laatste sync
- `icecat_product_id`: Icecat product ID
- `icecat_brand`: Merk uit Icecat
- `icecat_category`: Categorie uit Icecat
- `icecat_quality`: Data kwaliteit indicator
- `icecat_error_message`: Laatste foutmelding

### Scheduled Actions:

1. **Icecat: Sync New Products**
   - Frequentie: Elk uur
   - Batch: 10 producten
   - Doel: Nieuwe producten synchroniseren

2. **Icecat: Update Existing Products**
   - Frequentie: Dagelijks om 02:00
   - Batch: 100 producten
   - Doel: Bestaande producten bijwerken (>30 dagen oud)

## Dependencies

- `base`
- `product`
- `website_sale`
- Python: `requests` library

## Licentie

LGPL-3

## Support

Voor vragen of problemen, neem contact op met Nerbys.

## Changelog

### Version 18.0.1.0.0
- Initiële release
- Icecat JSON API integratie
- Automatische batch synchronisatie
- Configureerbaar via Website Settings
- Status tracking en error handling
