# TODO - Icecat Product Enrichment

## 🎯 Feature Request: Spec Filtering & Visibility Control

### Gewenste functionaliteit
Bij elke Icecat specificatie kunnen bepalen of:
1. ✅ Het een **filter optie** moet zijn op category pages (webshop)
2. ✅ Het **zichtbaar** moet zijn in de accordion op product detail page

### Huidige situatie
- ✅ Alle specs worden getoond in accordion op PDP
- ✅ Attribute sync werkt voor filtering op category pages
- ❌ Geen UI om per spec te configureren wat er moet gebeuren

### Gewenste oplossing
**Backend interface** om per specificatie te bepalen:
- `filterable` (boolean) - Toon als filter op category page
- `visible_in_accordion` (boolean) - Toon in PDP accordion

**Mogelijke implementaties:**
1. **Optie A:** Nieuwe tab "Icecat Specificaties Config" in Settings
   - Lijst van alle specs die gevonden zijn
   - Per spec: naam, category, checkbox filterable, checkbox visible
   
2. **Optie B:** Extend `product.attribute` model
   - Extra velden: `icecat_filterable`, `icecat_visible_accordion`
   - Werkt direct met bestaande attribute sync
   
3. **Optie C:** Nieuw model `icecat.specification.config`
   - `spec_name`, `spec_category`, `filterable`, `visible_accordion`
   - Los van product.attribute systeem

### Tech requirements
- Attribute sync (`_sync_product_attributes`) moet behouden blijven
- Accordion HTML generatie moet visibility settings respecteren
- Config moet persistent zijn (niet overschreven bij re-sync)
- Bij nieuwe specs: default `filterable=False`, `visible_accordion=True`

### Impact
- Minder ruis in filters (alleen relevante specs)
- Schonere accordions (onnodige specs verbergen)
- Betere UX voor eindklanten

---

## 📋 Backlog

- [ ] Image alt-text optimalisatie voor SEO
- [ ] Bulk sync progress indicator in UI
- [ ] Export/import van spec visibility config
- [ ] Multi-language support voor specs (als Icecat dit ondersteunt)
