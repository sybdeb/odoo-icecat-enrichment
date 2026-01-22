# Product Content Verrijking v19

Odoo 19 module voor automatische product content verrijking met meerdere databronnen.

## Features

### Multi-Source Enrichment
- **BarcodeLookup.com** - Gratis tier beschikbaar, goede basis data
- **Icecat** - Uitgebreide specificaties en professionele productdata
- Configureerbare prioriteit en volgorde van bronnen

### Intelligente Data Mapping
- Eerst lege velden vullen
- Optioneel gevulde velden overschrijven
- Per-veld configuratie: welke bron mag welk veld updaten
- Prijs wordt nooit overschreven (beschermd)

### Flexibele Configuratie
- Instelbare bron prioriteit:
  - BarcodeLookup eerst, dan Icecat
  - Icecat eerst, dan BarcodeLookup
  - Alleen BarcodeLookup
  - Alleen Icecat
- Veld-mapping: bepaal exact welke bron welk veld mag vullen/overschrijven
- Batch grootte configuratie voor dag/nacht runs

### Automatische Synchronisatie
- Nieuwe producten: kleine batches (10 producten/4 uur)
- Updates: grote batches (100 producten/nacht)
- Handmatige bulk acties mogelijk
- Sync status tracking per product

### Data Verrijking
- Product naam
- Beschrijvingen (kort & lang)
- Productafbeeldingen
- Specificaties (alleen Icecat)
- Key highlights accordion (Icecat)
- Merk/categorie informatie
- MPN tracking

## Installatie

Zie [INSTALL.md](INSTALL.md) voor gedetailleerde installatie instructies.

## Configuratie

### 1. Basis Instellingen
Ga naar: **Website > Configuratie > Instellingen > Product Verrijking**

### 2. BarcodeLookup Setup
1. Vink "BarcodeLookup Actief" aan
2. Voer je API key in (verkrijg via https://www.barcodelookup.com/api)
3. Klik "Test Connectie" om te valideren

### 3. Icecat Setup
1. Vink "Icecat Actief" aan
2. Voer username en password in
3. Kies Open (gratis) of Full (betaald) catalog
4. Klik "Test Connectie" om te valideren

### 4. Bron Prioriteit
Kies de volgorde waarin bronnen gebruikt worden:
- **BarcodeLookup eerst, dan Icecat** (aanbevolen) - Gebruik gratis BarcodeLookup quota, vul aan met Icecat
- **Icecat eerst, dan BarcodeLookup** - Best mogelijke specs eerst
- **Alleen BarcodeLookup** - Voor simpele webshops
- **Alleen Icecat** - Voor maximale product detail

### 5. Veld Mapping (Geavanceerd)
**Website > Configuratie > Product > Veld Mapping**

Configureer per veld:
- Welke bronnen het mogen vullen (BarcodeLookup / Icecat)
- Of overschrijven is toegestaan
- Notities per mapping

**Standaard gedrag:**
- Lege velden worden altijd gevuld (eerste beschikbare bron)
- Gevulde velden alleen overschrijven als toegestaan in mapping
- Prijs wordt nooit aangeraakt

## Gebruik

### Handmatig Enkel Product
1. Open een product
2. Zorg dat het een barcode heeft
3. Klik "Verrijk Product" button
4. Bekijk de "Content Verrijking" tab voor details

### Bulk Verrijking
1. Ga naar Product lijst
2. Selecteer meerdere producten
3. **Actie > Bulk Product Verrijking**
4. Kies opties:
   - Force Update: ook al verrijkte producten updaten
   - Bron Override: tijdelijk andere bron prioriteit
5. Klik "Start Verrijking"

### Automatisch via Cron
Twee cron jobs draaien automatisch:
- **Nieuwe Producten**: Elke 4 uur, 10 producten per batch
- **Updates**: Elke nacht om 02:00, 100 producten per batch

Configureer batch groottes in Website Settings.

## Sync Logs

Bekijk verrijkings geschiedenis:
**Website > Configuratie > Product > Sync Logs**

Per log zie je:
- Sync type (manual/new/update)
- Aantal succesvol/errors/geen data
- Gebruikte bronnen
- Tijdsduur
- Error details (indien van toepassing)

## Product Filters

Filter producten op verrijkings status:
- Niet Verrijkt
- Verrijkt
- Verrijkings Errors
- Geen Data Beschikbaar
- Data van BarcodeLookup
- Data van Icecat

## Aanbevolen Strategie

### Voor Maximale Data + Minimale Kosten

```
Prioriteit: BarcodeLookup eerst, dan Icecat
BarcodeLookup: Actief (gratis tier)
Icecat: Actief (Open Catalog - gratis)
```

**Wat gebeurt er:**
1. Eerst wordt BarcodeLookup geprobeerd (gratis quota)
2. Bij geen/weinig data → Icecat (onbeperkt gratis + betere specs)
3. Icecat overschrijft met rijkere data (specs, betere beschrijvingen)
4. Je houdt mooie Icecat uitklapbare specificaties op PDP

**Resultaat:**
- Altijd de beste beschikbare data
- Gratis BarcodeLookup calls eerst
- Icecat vult aan met professionele specs
- Geen conflicten (Icecat wint op kwaliteit)

## Support

Voor vragen of issues:
- Email: support@nerbys.nl
- Website: https://www.nerbys.nl

## Licentie

LGPL-3

## Credits

Ontwikkeld door Nerbys
