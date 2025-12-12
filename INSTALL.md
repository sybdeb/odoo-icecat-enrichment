# Installatie Instructies - Product Content Verrijking

## Vereisten

- Odoo 19.0
- Python 3.10+
- `requests` library
- Modules: `product`, `website_sale`, `product_google_category`

## Installatie Stappen

### 1. Module Installeren

```bash
# Kopieer de module naar je Odoo addons directory
cp -r product_content_verrijking /path/to/odoo/addons/

# Of maak een symlink
ln -s /path/to/product_content_verrijking /path/to/odoo/addons/
```

### 2. Update Addons Lijst

In Odoo:
1. Ga naar **Apps**
2. Klik op menu (☰) → **Update Apps List**
3. Bevestig update

### 3. Installeer Module

1. Zoek naar "Product Content Verrijking"
2. Klik **Install**

### 4. Configureer Data Bronnen

#### BarcodeLookup.com (Optioneel)

1. Ga naar https://www.barcodelookup.com/api
2. Meld je aan voor een gratis account
3. Kopieer je API key
4. In Odoo: **Website > Configuratie > Instellingen**
5. Scroll naar "Product Verrijking"
6. Vink "BarcodeLookup Actief" aan
7. Plak je API key
8. Klik "Test Connectie"

**Gratis Tier:**
- 100 requests/dag
- Basis product data
- 1 foto
- Perfect voor kleine webshops

#### Icecat (Aanbevolen)

1. Ga naar https://icecat.biz/en/menu/register/index.html
2. Registreer een account
3. Kies Open Catalog (gratis) of Full Catalog (betaald)
4. Kopieer username en password
5. In Odoo: **Website > Configuratie > Instellingen**
6. Scroll naar "Icecat Configuratie"
7. Vink "Icecat Actief" aan
8. Voer username en password in
9. Kies Catalog Type
10. Klik "Test Connectie"

**Open Catalog (Gratis):**
- Grote merken (Samsung, HP, Dell, etc.)
- Volledige specificaties
- Multiple afbeeldingen
- Onbeperkt aantal requests

**Full Catalog (Betaald):**
- Alle merken
- Premium content
- Vereist licentie

### 5. Configureer Bron Prioriteit

In **Website > Configuratie > Instellingen > Product Verrijking**:

**Aanbevolen voor beginners:**
```
Bron Prioriteit: "BarcodeLookup eerst, dan Icecat"
```

Dit gebruikt:
1. Eerst gratis BarcodeLookup tier
2. Dan onbeperkt gratis Icecat Open
3. Beste specs van Icecat
4. Minimale kosten

### 6. Configureer Veld Mapping (Optioneel)

Voor geavanceerde controle over welke bron welk veld mag updaten:

1. Ga naar **Website > Configuratie > Product > Veld Mapping**
2. Klik **Create**
3. Kies een veld (bijv. "Product Naam")
4. Vink bronnen aan die dit veld mogen vullen
5. Vink "Overschrijven Toestaan" aan indien gewenst
6. Sla op

**Default gedrag zonder mapping:**
- Name: beide bronnen, niet overschrijven
- Description: Icecat voorrang, wel overschrijven
- Image: beide bronnen, niet overschrijven

### 7. Test de Installatie

1. Maak een test product met een bekende barcode
   - Bijvoorbeeld: `5449000000996` (Coca-Cola)
2. Klik "Verrijk Product" button
3. Controleer de "Content Verrijking" tab
4. Verifieer dat data correct is ingevuld

## Verificatie Checklist

- [ ] Module geïnstalleerd zonder errors
- [ ] BarcodeLookup API test succesvol (indien gebruikt)
- [ ] Icecat API test succesvol
- [ ] Bron prioriteit geconfigureerd
- [ ] Test product succesvol verrijkt
- [ ] Cron jobs actief (check in Settings > Technical > Scheduled Actions)

## Cron Jobs

Twee cron jobs worden automatisch aangemaakt:

### 1. Nieuwe Producten
- **Naam:** Product Verrijking: Nieuwe Producten
- **Frequentie:** Elke 4 uur
- **Batch:** 10 producten
- **Functie:** Verrijkt nieuwe producten met barcode

### 2. Update Bestaande
- **Naam:** Product Verrijking: Update Bestaande  
- **Frequentie:** Dagelijks om 02:00
- **Batch:** 100 producten
- **Functie:** Update producten ouder dan 30 dagen

**Cron configuratie aanpassen:**
1. Ga naar **Settings > Technical > Scheduled Actions**
2. Zoek "Product Verrijking"
3. Pas interval/batch size aan indien gewenst

## Troubleshooting

### "Geen credentials geconfigureerd"
- Controleer of je API keys/credentials correct zijn ingevuld
- Klik "Test Connectie" om te valideren

### "Product niet gevonden in database"
- Barcode bestaat niet in de bron
- Probeer andere barcode
- Check of je de juiste Icecat catalog type hebt (Open vs Full)

### "API timeout"
- Internet connectie probleem
- Verhoog timeout in code indien nodig

### Cron jobs draaien niet
- Check of "Automatische Verrijking Actief" aan staat
- Verifieer cron jobs in Technical > Scheduled Actions
- Check Odoo cron worker is actief

### Velden worden niet overschreven
- Check Veld Mapping configuratie
- "Overschrijven Toestaan" moet aan staan
- Of veld is leeg (wordt altijd gevuld)

## Ondersteuning

Voor hulp:
- Email: support@nerbys.nl
- Website: https://www.nerbys.nl

## Upgrades

Bij updates:
1. Update module code
2. Ga naar Apps
3. Zoek module
4. Klik "Upgrade"
5. Check changelog voor breaking changes
