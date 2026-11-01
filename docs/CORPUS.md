# CORPUS.md — curated drug list

> **Role changed (2026-10-29, DECISIONS.md D14/D18):** there is no database or ingested corpus anymore; tools query openFDA live for *any* product. This list is now the **eval and fixture drug set**: the products the golden-set queries and recorded test fixtures are built around. The selection rules below (D11/D12) still matter, because tools apply them at request time.

The curated set of drugs for the corpus. This is the human worksheet; a machine-readable manifest is derived from it later. Scope + selection rules: see `DECISIONS.md` D2, D11, D12.

- **Unit = product** (a specific formulation), not brand. Each product → one `drugs` row.
- For each brand, fill in the meaningfully-different **formulations** (differ by strength, form/release, or population). Skip cosmetic near-duplicates (caplet vs gelcap, package size).
- **Search by**: `brand` = `openfda.brand_name.exact`; `generic` = `openfda.generic_name.exact` (older brand names are often absent; the live records sit under the generic).
- Selection per formulation (D12): prefer `is_original_packager: true` → collapse repackagers via `original_packager_product_ndc` → newest `effective_time`.

## OTC

| # | Brand | Generic | Search by | Showcases | Formulations to keep (fill in) |
|---|---|---|---|---|---|
| 1 | Tylenol | acetaminophen | brand | strengths/forms/Children's; liver warning | |
| 2 | Advil | ibuprofen | brand | NSAID; strengths, Infants/Children's, PM combo | |
| 3 | Aleve | naproxen | brand | NSAID, 12-hr dosing (interval contrast) | |
| 4 | Benadryl | diphenhydramine | brand | allergy vs sleep-aid; Children's; sedation | |
| 5 | Claritin | loratadine | brand | non-drowsy antihistamine (contrast to Benadryl) | |
| 6 | Prilosec OTC | omeprazole | brand/generic | PPI; GI; clopidogrel interaction | |

## Prescription

| # | Brand | Generic | Search by | Showcases | Formulations to keep (fill in) |
|---|---|---|---|---|---|
| 7 | Lipitor | atorvastatin | brand | statin; 10/20/40/80 mg; CYP3A4 interactions; pregnancy contra | |
| 8 | Coumadin | warfarin | generic | anticoagulant; narrow therapeutic index; big interaction list; dose-critical | |
| 9 | Glucophage | metformin | generic | diabetes; IR vs ER; boxed warning; renal population | |
| 10 | Zestril / Prinivil | lisinopril | generic | ACE inhibitor; strengths; pregnancy boxed warning | |
| 11 | Amoxil | amoxicillin | generic | antibiotic; pediatric weight-based dosing; caps/chewable/suspension | |
| 12 | Deltasone | prednisone | generic | corticosteroid; many strengths; taper dosing | |
| 13 | Ozempic | semaglutide | brand | GLP-1; dose escalation; boxed warning; injection | |
| 14 | Ventolin / ProAir | albuterol | brand | rescue inhaler; asthma; pediatric; non-oral route | |
| 15 | Zoloft | sertraline | generic | SSRI; boxed warning (youth suicidality); strengths; pediatric | |

## Notes / caveats
- Warfarin: brand "Coumadin" may be sparse; current records also appear as generic "WARFARIN SODIUM" and the brand "Jantoven".
- Older brands (Amoxil, Deltasone, Zestril/Prinivil, Glucophage): search by generic; the brand string may return little.
- Mix intent: keep a genuine OTC/prescription balance so tools show both the short OTC "Drug Facts" schema and the richer prescription schema (boxed warnings, interactions, population sections).
