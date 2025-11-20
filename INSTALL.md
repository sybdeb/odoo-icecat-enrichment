# Installatie Instructies - Icecat Product Enrichment

## Stap 1: Module installeren

De module staat al in je addons folder. Voer deze commando's uit:

```bash
cd /c/Users/Sybde/Projects/odoo-dev

# Herstart Odoo (via je bestaande script)
./restart-odoo.sh
```

## Stap 2: Module activeren in Odoo

1. Log in op Odoo als administrator
2. Ga naar **Apps**
3. Klik op "Update Apps List" (mogelijk moet je eerst developer mode aanzetten)
4. Zoek naar "Icecat Product Enrichment"
5. Klik op **Install**

## Stap 3: Configureer je Icecat credentials

1. Ga naar **Website > Configuration > Settings**
2. Scroll naar beneden tot je **Icecat Configuration** ziet
3. Vul in:
   - **Icecat Username**: `NerbysNL`
   - **Icecat Password**: `DG.BQBEH.005`
   - **Catalog Type**: `Icecat Open Catalog` (of Full als je daar toegang toe hebt)
4. Zorg dat deze opties aangevinkt zijn:
   - ✅ Enable Auto Sync
   - ✅ Sync Description
   - ✅ Sync Images
   - ✅ Sync Specifications
5. Controleer de batch groottes:
   - New Products Batch Size: `10`
   - Update Batch Size: `100`
6. Klik op **Save**

## Stap 4: Test met een product

1. Ga naar **Sales > Products > Products**
2. Open een bestaand product of maak een nieuw product
3. Zorg dat het product een **Barcode** (EAN/GTIN) heeft
4. Klik op de knop **Sync with Icecat**
5. Je zou een notificatie moeten zien of het gelukt is

## Stap 5: Check de automatische synchronisatie

De module heeft 2 scheduled actions aangemaakt:

### Icecat: Sync New Products
- **Wanneer**: Elk uur
- **Wat**: Synchroniseert 10 nieuwe producten die nog niet zijn gesynchroniseerd
- **Check**: Ga naar Settings > Technical > Automation > Scheduled Actions
- **Zoek**: "Icecat: Sync New Products"

### Icecat: Update Existing Products  
- **Wanneer**: Elke nacht om 02:00
- **Wat**: Update 100 producten die langer dan 30 dagen geleden zijn gesynchroniseerd
- **Check**: Ga naar Settings > Technical > Automation > Scheduled Actions
- **Zoek**: "Icecat: Update Existing Products"

## Stap 6: Bulk synchronisatie (optioneel)

Als je meerdere producten in één keer wilt synchroniseren:

1. Ga naar **Sales > Products > Products**
2. Filter op "Not Synced with Icecat" (nieuwe filter in de zoekbalk)
3. Selecteer de producten die je wilt synchroniseren
4. Klik op **Action > Sync with Icecat**
5. Kies je opties:
   - Sync Type: "Selected Products Only"
   - Batch Size: 10 of meer
6. Klik op **Start Sync**

## Troubleshooting

### "Icecat credentials not configured"
- Controleer of je de username en password hebt ingevuld in Website Settings
- Zorg dat er geen extra spaties zijn

### "Product not found in Icecat database"
- Niet alle EAN codes staan in Icecat
- Controleer of de EAN code correct is
- Probeer het product handmatig op https://icecat.biz te zoeken

### "Authentication failed"
- Controleer je Icecat username en password
- Test je credentials op https://icecat.biz
- Let op hoofdletters/kleine letters in het wachtwoord

### Producten worden niet automatisch gesynchroniseerd
- Check of "Enable Auto Sync" aanstaat in de settings
- Controleer of de scheduled actions active zijn
- Check de logs: Settings > Technical > Logging

## Handige filters in de product lijst

Na installatie heb je deze filters beschikbaar:
- **Not Synced with Icecat**: Producten die nog moeten worden gesynchroniseerd
- **Synced with Icecat**: Succesvol gesynchroniseerde producten  
- **Icecat Sync Errors**: Producten waarbij een fout optrad
- **Pending Icecat Sync**: Producten die in de wachtrij staan

## Status indicatoren

In de product lijst zie je badges:
- 🟢 **Synced**: Product is succesvol gesynchroniseerd
- 🔵 **Pending**: Product staat in de wachtrij
- 🔴 **Error**: Er is een fout opgetreden
- 🟡 **No Data**: Product niet gevonden in Icecat
- ⚪ **Not Synced**: Product is nog niet gesynchroniseerd

## Volgende stappen

1. Zorg dat al je producten een EAN/GTIN barcode hebben
2. Laat de automatische synchronisatie een dag draaien
3. Check de resultaten en pas de batch groottes aan indien nodig
4. Voor problemen: check de Icecat tab op het product voor foutmeldingen

## Extra informatie

- De module gebruikt de Icecat JSON API
- Alleen producten met een barcode worden gesynchroniseerd
- Product data wordt alleen overschreven als je dat hebt ingesteld
- Images worden automatisch gedownload en opgeslagen
- Specificaties worden toegevoegd aan de Sales Description

Veel succes met je Icecat integratie! 🚀
