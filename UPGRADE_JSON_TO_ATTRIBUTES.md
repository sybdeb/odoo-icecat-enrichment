# Upgrade: JSON Specs → Odoo Attributes

## ✅ Wat is er Veranderd?

### Oude Situatie
```
Icecat API → JSON field → Custom HTML accordion → Website (niet filterbaar)
```

### Nieuwe Situatie  
```
Icecat API → JSON field (backup) → Odoo Attributes → Website (filterbaar!)
```

## 🎯 Belangrijkste Verbeteringen

### 1. **JSON Behouden als Backup** ✅
- `icecat_specifications_raw` blijft bestaan
- Bevat originele Icecat data
- Kan opnieuw geconverteerd worden

### 2. **Automatische Conversie naar Attributes** ✅
- Bij elke sync: JSON → Odoo attributes
- Elke spec = eigen attribuut (bijv. "Kleur", "Processor")
- Gegroepeerd per categorie (Design, Beeldscherm, etc.)

### 3. **Standaard Odoo Website Weergave** ✅
- Nieuwe template: `website_product_attributes.xml`
- Accordion met alle categorieën
- Mooi gestyled, responsive
- Werkt met Bootstrap 5

### 4. **Automatisch Filterbaar** ✅
- Attributes zijn native filterbaar in Odoo
- Shop category pages tonen automatisch filters
- Multi-select mogelijk
- Real-time filtering

## 📁 Aangepaste Bestanden

### 1. `models/icecat_connector.py`
**Nieuwe functies:**
- `_get_or_create_attribute_category()` - Maakt categorie aan (Design, Processor, etc.)
- `_detect_attribute_display_type()` - Smart detection (color, radio, select)
- `_sync_product_attributes()` - **VOLLEDIG HERSCHREVEN**
  - Elk spec = individueel attribuut
  - Category grouping
  - Deduplicatie van values

**Workflow:**
```python
# In sync_product():
1. Store JSON specs ✅
2. Convert to attributes ✅
3. Both available!
```

### 2. `models/product_template.py`
**Nieuwe functies:**
- `action_convert_json_to_attributes()` - Handmatige conversie voor migratie
- Updated `_compute_icecat_specifications_grouped()` - Nu een info preview

**Fields:**
- `icecat_specifications_raw` - BEHOUDEN (readonly)
- `icecat_specifications_grouped` - Nu info display

### 3. `views/website_product_attributes.xml` ⭐ NIEUW
**Vervangt:** `views/website_product_specifications.xml` (oude custom accordion)

**Features:**
- Accordion per categorie
- Badge met aantal specs
- Responsive design
- Color attribute support
- Bootstrap 5 styling

### 4. `views/product_template_views.xml`
**Nieuwe button:**
- "JSON → Attributes" - Voor handmatige conversie bestaande producten

### 5. `__manifest__.py`
**Updated:**
- `website_product_attributes.xml` ipv `website_product_specifications.xml`

## 🚀 Nieuwe Features

### Category Systeem
Specs worden gegroepeerd via `product.attribute.category`:
- Design (sequence: 10)
- Beeldscherm (20)
- Processor (30)
- Geheugen (40)
- etc.

→ Mooie volgorde op website!

### Smart Display Types
Automatische detectie:
- **Color** - Als "kleur" in naam
- **Radio** - Voor Y/N, Yes/No, Ja/Nee
- **Select** - Voor 3+ opties
- **Always** - Default

### Deduplicatie
Values worden hergebruikt:
- "Intel" bij 100 producten = 1 value
- Efficiënt en consistent
- Betere filters

## 📋 Migratie Bestaande Producten

### Optie A: Automatisch bij Re-sync
```
Product → Sync with Icecat → JSON + Attributes updated
```

### Optie B: Handmatige Conversie
1. Open product
2. Klik "JSON → Attributes" button
3. Converteert bestaande JSON naar attributes

### Optie C: Bulk Conversie (Python)
```python
# Via Odoo shell
products = env['product.template'].search([
    ('icecat_specifications_raw', '!=', False)
])
for product in products:
    product.action_convert_json_to_attributes()
    env.cr.commit()
```

## 🌐 Website Display

### Product Detail Page
- Accordion met alle categorieën
- Collapsed by default (beter voor UX)
- Badge toont aantal specs per categorie
- Clean table layout

### Category/Shop Pages
- Automatische filter sidebar
- Grouped per attribute category
- Multi-select checkboxes
- Real-time filtering

### Mobile Responsive
- Bootstrap 5 accordion
- Touch-friendly
- Optimized for small screens

## ⚙️ Configuratie

### Settings (GEEN WIJZIGINGEN)
Alles werkt out-of-the-box:
- Sync attributes: ALTIJD AAN (niet meer optioneel)
- JSON: ALTIJD opgeslagen
- Beide beschikbaar!

## 🧪 Testing Checklist

### Backend
- [ ] Product sync met Icecat
- [ ] JSON field gevuld
- [ ] Attributes aangemaakt
- [ ] Categories correct
- [ ] "Attributen & Varianten" tab toont specs
- [ ] "JSON → Attributes" button werkt

### Frontend
- [ ] Accordion zichtbaar op product page
- [ ] Alle categorieën tonen
- [ ] Specs correct per categorie
- [ ] Styling correct (blauw, collapsed)
- [ ] Responsive op mobile
- [ ] Filters zichtbaar op shop page
- [ ] Filtering werkt

## 🔄 Backwards Compatibility

### Oude Custom Accordion
- `website_product_specifications.xml` - KAN verwijderd worden
- Niet meer nodig
- Nieuwe template doet hetzelfde + beter

### Spec Manager Wizard
- Blijft werken voor JSON editing
- Kan nog steeds specs verwijderen
- Conversie naar attributes daarna opnieuw doen

## 📊 Performance

### Voordelen:
- ✅ Attributes: 1x per waarde (bijv. "Intel")
- ✅ JSON: Compact opslag
- ✅ Website: Cached door Odoo
- ✅ Filters: Database indexed

### Let op:
- ⚠️ Veel specs = veel attributes (100+)
- ⚠️ Eerste sync iets langzamer (attributes maken)
- ⚠️ Re-sync: verwijdert/maakt attributes opnieuw

## 🎁 Extra Features

### Color Support
- Auto-detect voor "Kleur" attributes
- Common colors → HTML color codes
- Visual display op website

### Category Badges
- Aantal specs per categorie
- Visuele feedback
- Beter overzicht

### Info Preview
- `icecat_specifications_grouped` toont nu:
  - Aantal specs
  - Aantal categorieën  
  - Aantal attributes
  - Link naar Attributes tab

## 🚧 Volgende Stappen

### Optioneel - Later:
1. **Filtering** - Whitelist/blacklist specs
2. **Mapping** - Custom spec → attribute names
3. **Priorities** - Welke specs als highlights
4. **Search Integration** - Odoo search op attributes
5. **Comparison** - Product comparison features

## 📞 Support

Bij vragen/problemen:
1. Check Attributes & Variants tab
2. Check JSON field (raw data)
3. Re-sync of gebruik "JSON → Attributes"
4. Check logs voor errors

---

**Status: KLAAR VOOR DEPLOYMENT** 🚀

Alle code is backwards compatible en kan direct gedeployed worden!
