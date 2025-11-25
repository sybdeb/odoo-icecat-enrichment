# TODO voor morgen - Icecat specificaties fixes

## Huidige situatie
- ✅ Icecat sync werkt met 149 attributen (was 8)
- ✅ Accordion op website toont gegroepeerde specs
- ✅ Backend Kenmerken & varianten tab zichtbaar
- ❌ Dubbele accordion secties op website (lege headers onderaan)
- ❌ Backend toont 149 attributen in lange platte lijst zonder groepering

## Analyse van de suggestie

### Wat we NIET hebben (verschil met suggestie)
- Geen `product.specification.line` model
- Geen `presentation_side` veld
- We gebruiken **Odoo's standaard product attributes systeem**:
  - `product.attribute` (master attributen)
  - `product.attribute.value` (mogelijke waarden)
  - `product.template.attribute.line` (koppeling product ↔ attribuut)

### Onze huidige architectuur
```
models/icecat_connector.py:
  - _sync_product_attributes() creëert voor elke Icecat spec:
    * attribute met name format: "Beeldscherm: Beeldschermdiagonaal"
    * attribute.value met de waarde (bijv. "34")
    * attribute_line koppelt aan product
```

### Wat wel bruikbaar is uit de suggestie

#### 1. **Website dubbele accordion** (PRIORITEIT 1)
**Probleem**: Odoo's `website_sale_comparison` module toont een lege accordion
**Oplossing**:
```xml
<!-- In views/product_website_views.xml -->
<template id="hide_product_accordion" inherit_id="website_sale.product_accordion">
    <xpath expr="//div[@id='product_accordion']" position="replace"/>
</template>
```

#### 2. **Backend gegroepeerde weergave** (PRIORITEIT 2)
**Twee opties**:

**Optie A: Computed HTML veld** (probeerden vandaag, werkte niet goed)
- Probleem: HTML widget in form view rendeert accordion niet interactief
- BS5 accordion heeft client-side JS nodig

**Optie B: Custom tree view met grouping** ⭐ BESTE OPTIE
```python
# In models/product_template.py
@api.depends('attribute_line_ids')
def _compute_attribute_groups(self):
    """Group attributes by category for tree view"""
    for product in self:
        groups = {}
        for line in product.attribute_line_ids:
            # Parse "Beeldscherm: Resolutie" format
            if ':' in line.attribute_id.name:
                category = line.attribute_id.name.split(':')[0].strip()
                if category not in groups:
                    groups[category] = []
                groups[category].append(line)
        # Store as JSON or use related model
        product.attribute_groups_json = json.dumps(groups)
```

```xml
<!-- In views/product_template_views.xml -->
<field name="attribute_line_ids" 
       context="{'group_by': 'attribute_id.category_id'}"
       options="{'group_by_no_leaf': 1}">
    <tree>
        <field name="attribute_id"/>
        <field name="value_ids" widget="many2many_tags"/>
    </tree>
</field>
```

**Optie C: Nested relational field** (ADVANCED)
- Maak `product.attribute.category` model
- Link via `attribute_id.category_id`
- Gebruik grouped tree view

#### 3. **Filtering op website** (PRIORITEIT 3 - TOEKOMST)
- Onze attributen zijn al in DB als `product.template.attribute.line`
- Odoo's website builder kan hier filters op maken
- Geen extra code nodig, enkel configuratie in website builder

## Actiepunten voor morgen

### Quick wins (30 min)
1. ✅ Fix dubbele accordion door `product_accordion` te verbergen
2. ⚠️ Test of dit de lege headers weghaalt

### Backend groepering (1-2 uur)
3. Probeer grouped tree view met category extraction
4. Als dat niet werkt: Maak lightweight `attribute.category` model

### Filtering (optioneel, als tijd over)
5. Documenteer hoe medewerkers filters kunnen toevoegen via website builder
6. Test met één categorie (bijv. "Beeldscherm")

## Technische details

### Huidige data structuur
```sql
-- Product attributes na sync
SELECT 
    pa.name as attribute_name,           -- "Beeldscherm: Resolutie"
    pav.name as value_name,               -- "3440 x 1440"
    ptal.product_tmpl_id
FROM product_template_attribute_line ptal
JOIN product_attribute pa ON ptal.attribute_id = pa.id
JOIN product_attribute_value pav ON pav.id = ANY(ptal.value_ids)
WHERE ptal.product_tmpl_id = 110
ORDER BY pa.name;
```

### Controller data flow (werkt al!)
```python
# controllers/main.py
def _prepare_product_values(self, product, ...):
    attr_groups = defaultdict(list)
    for line in product.attribute_line_ids:
        group, name = parse_attribute_name(line.attribute_id.name)
        attr_groups[group].append((name, value))
    values['attribute_groups'] = sorted(attr_groups.items())
```

## Verschillen met suggestie

| Suggestie gebruikt | Wij gebruiken | Reden |
|-------------------|---------------|-------|
| `product.specification.line` | `product.template.attribute.line` | Odoo standard |
| `presentation_side` veld | Parse uit `attribute.name` | Werkt met std fields |
| Custom model | Computed grouping | Minder DB overhead |
| TransientModel groups | Controller grouping | Al werkend voor website |

## Vragen voor gebruiker morgen
1. Wil je echte groepering in backend of is platte lijst OK? (gebruikers kunnen zoeken)
2. Moeten medewerkers specs kunnen **bewerken** of alleen **bekijken**?
3. Website filtering: via Odoo builder of custom code?

## Resources
- Odoo docs: Product Attributes - https://www.odoo.com/documentation/18.0/applications/sales/sales/products_prices/products/variants.html
- Grouped tree views: https://www.odoo.com/documentation/18.0/developer/reference/user_interface/view_records.html#tree
- Website product filters: https://www.odoo.com/documentation/18.0/applications/websites/ecommerce/products.html
