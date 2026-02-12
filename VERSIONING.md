# Versioning Beleid

## Format
Alle versies volgen het formaat: `19.0.MAJOR.MINOR.PATCH`

- **19.0** = Odoo versie (vast)
- **MAJOR** = Grote features/breaking changes (1, 2, 3, ...)
- **MINOR** = Nieuwe features/verbeteringen (0, 1, 2, ...)
- **PATCH** = Bugfixes/kleine aanpassingen (0, 1, 2, ...)

## Regels
1. **Elke fix/feature MOET een nieuwe versienummer krijgen**
2. **Geen enkele deployment zonder versie bump**
3. **Git tag op elke versie: `v19.0.MAJOR.MINOR.PATCH`**

## Voorbeelden
- `19.0.1.0.0` → Initiële productie versie (Icecat branding)
- `19.0.1.1.0` → Rebrand naar DBW Product Enrichment
- `19.0.1.1.1` → Bugfix accordion JavaScript
- `19.0.1.2.0` → Nieuwe feature: multi-provider support
- `19.0.2.0.0` → Breaking change: nieuwe database structuur

## Version History
| Versie | Datum | Omschrijving | Tag |
|--------|-------|--------------|-----|
| 19.0.1.0.0 | 2026-01-20 | Production baseline (Icecat) | v19.0.1.0.0-pro-gating |
| 19.0.1.1.0 | 2026-01-22 | Rebrand to DBW Product Enrichment | v19.0.1.1.0-rebrand |

## Deployment Workflow
1. Lokale wijzigingen maken in workspace
2. Versienummer bumpen in `__manifest__.py`
3. Testen op DEV server
4. Copy naar `dev_versies/dbw_product_enrichment/v19.0.MAJOR.MINOR.PATCH/`
5. Git commit + tag: `git tag v19.0.MAJOR.MINOR.PATCH`
6. Bij succes: copy naar `live_versies/`
7. Deploy naar productie
