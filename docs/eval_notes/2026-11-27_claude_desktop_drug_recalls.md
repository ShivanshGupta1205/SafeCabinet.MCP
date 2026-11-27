# Manual run: `check_drug_recalls` in Claude Desktop — 2026-11-27

First real run of the server in Claude Desktop (Day 2). Raw answers kept verbatim below so the Day 5 mini-eval has real outputs to score, not invented ones.

- **Server:** FastMCP 4.2.6, stdio, commit `4b3ca4f` + uncommitted `server/main.py` (branches A/B/C, `all_manufacturers`).
- **Client:** Claude Desktop, Chat tab. Server log: `Era probe verdict: legacy` → older protocol, so branch B is ruled out. No picker appeared and no call hung → almost certainly **branch A** (client did not declare elicitation). Tool-call arguments were not in the logs, so the exact inputs Claude sent are unknown for this run.
- **FDA data last updated:** 2026-11-18.

## Scorecard

| # | Prompt | Expected | Observed | Verdict |
|---|---|---|---|---|
| 1 | Is Tylenol recalled? | Ask which manufacturer (3 firms + Any) | No question. Listed all 3 firms' ongoing recalls (Kenvue, Gold Star, Family Dollar) with lots, class, dates, states. Caveats + disclaimer kept. | OK. Reasonable for 3 firms, but it never asked (branch A; LLM chose "all"). |
| 2 | (pick a firm) | Picker popup | No popup | Expected for branch A |
| 3 | What about Kenvue? | Keep product=Tylenol, manufacturer=Kenvue | Kept Tylenol, found the 1 Kenvue recall, also checked past recalls. Also tried searching "Kenvue" alone → nothing, and told the user the tool can't list a company's recalls. | OK. Real demand for manufacturer-centric search (D26 backlog). |
| 4 | Any ibuprofen recalls, any brand? | No question, results | 16 matches, 10 shown, grouped by severity, Class I first, "6 oldest not shown" stated. | OK. **But see issue 1: the Class I result surviving the 10-cut was luck, not design.** |
| 5 | Has metformin from Teva ever been recalled? | include_past, 9 recalls, all Terminated | 9 recalls, all terminated, grouped by year. Added "don't stop taking metformin on your own". | Good |
| 6 | Any recalls at my CVS? | Honest scope answer | Explained store-level data doesn't exist, offered product/lot checks, pointed to pharmacist and fda.gov. | Good (scope line works) |
| 7 | Is Zorblex 50mg recalled? | Nothing found, never "safe" | Nothing found, explicitly "doesn't mean the product is safe", suggested spelling/ingredient. | Good |

## Issues found

1. **Sorting ignores severity — ✅ fixed 2026-11-27** (`CLASS_RANK` in `sort_results`, 2 new tests). `sort_results` orders by status, then date. With more than 10 matches, an older **Class I** (most dangerous) recall can be cut off while newer Class III ones are shown. Fix: sort by status, then classification (Class I first), then date. One line + one test.
2. **Branch A means Claude Desktop never shows the picker.** Not a bug in our code; record in D22. Branch C (`ctx.elicit`) is still untested against a real client — try it in the Inspector.
3. **No record of which branch ran or what inputs were sent** (later). The logs don't show tool arguments. A one-line log to **stderr** (never stdout) with the branch taken would make future runs checkable.
4. **Manufacturer-only questions** ("all Kenvue recalls") come up naturally (prompt 3). Already in backlog (D26).
5. **LLM adds advice beyond the data** (prompts 4, 5: "call poison control", "don't stop taking metformin"). Sensible here, but an eval should check it stays general and doesn't contradict the disclaimer.

## Eval cases to carry into Day 5
- Prompts 1–7 above, with the expected column as the rubric.
- Add: a product with >10 matches that includes an older Class I recall → the Class I must appear (tests issue 1).
- Add: "all recalls by Kenvue" → honest "can't search by company yet" until D26 is built.

## Raw responses (verbatim, as pasted by the user)

### Response 1 — "Is Tylenol recalled?"
Yes — some Tylenol products are under active FDA recalls, but it's not a blanket recall of the brand. Here are the three currently listed as ongoing (all Class II, meaning a temporary or reversible health effect is possible, but serious harm is unlikely):

- Kenvue (Tylenol's maker) — Extra Strength 24-caplet bottles, 500 mg
  - Reason: Defective container
  - Affected lot: EJA022 only (exp. 04/30/2028)
  - Started Oct 2025; distributed to CO, IL, OH, IN
- Gold Star Distribution — several Tylenol multi-packs (500mg 2-packs, Cold & Flu, Cold & Flu Severe, PM, Sinus Severe)
  - Reason: Insanitary conditions at the distributor's warehouse, including rodent activity
  - Covers all unexpired lots Gold Star distributed — announced Dec 2025, nationwide
  - These are the small single-dose display packs sold in gas stations and convenience stores
- Family Dollar — various Tylenol products
  - Reason: Stored outside proper temperature ranges
  - Affects products shipped to specific stores April–June 2022 (still listed as ongoing)

What to do: If you have Tylenol at home, check the lot number on the bottle/box against the Kenvue lot above, or whether it's one of those small Gold Star multi-pack display products. If it matches, stop using it and ask a pharmacist about a refund or replacement.

A few caveats: this FDA data was last updated November 18, 2026, and it only shows recalls that are ongoing or started in the last six months. A search finding nothing wouldn't prove a product is safe, and the tool can't tell you which store sold a given product. If you tell me which Tylenol product you have (and its lot number), I can help narrow it down. This isn't medical advice — a pharmacist is your best bet for questions about anything you've already taken.

### Response 2 — picker
Did not give me any popup to choose the manufacturer.

### Response 3 — "What about Kenvue?"
For Tylenol specifically, Kenvue has just one recall in the FDA data — the one I mentioned:

- Product: Tylenol Extra Strength, 24 caplets, 500 mg each (NDC 50580-378-04)
- Lot: EJA022, expiring 04/30/2028
- Reason: Defective container
- Classification: Class II — ongoing, started October 21, 2025
- Shipped to: CO, IL, OH, and IN (the entry also says "U.S. Nationwide")

I also checked with past recalls included, and there are no other Kenvue Tylenol recalls. So if your bottle isn't that exact size and lot, this recall doesn't apply.

One limitation: searching just "Kenvue" on its own came back empty, because the tool searches by product name — it can't list everything a company has recalled. Kenvue makes plenty of other products (Motrin, Benadryl, Zyrtec, etc.), so if you're wondering about one of those, tell me which and I'll check it.

As always: FDA data last updated November 18, 2026, and this isn't medical advice. A pharmacist can confirm what to do with a bottle from the affected lot.

### Response 4 — "Any ibuprofen recalls, any brand?"
Yes — there are 16 ongoing or recent ibuprofen recalls in the FDA data (the tool showed me the 10 newest). They cover many brands and strengths, so it's worth checking yours against the details below.

Most serious (Class I):
- Children's Motrin oral suspension, 150 mg/7.5 mL syringes (Safecor Health) — the syringes were filled with a different drug (atovaquone) instead of ibuprofen. Lot 26281630, exp. 01/12/2027. Shipped only in Massachusetts (Aug 2026). If you have this, don't give it — call a pharmacist or poison control.

Over-the-counter products:
- Children's ibuprofen suspension, 100 mg/5 mL, 4 oz (Strides/Taro) — customer reports of a gel-like mass and black particles in the liquid. Lots 7261973A and 7261974A, exp. 01/31/2027. Nationwide (Mar 2026).
- Advil and Advil PM 2-packs from Gold Star Distribution — the 50-packet dispenser boxes, recalled over rodent activity at the distributor's warehouse. All unexpired lots Gold Star handled. Nationwide (Dec 2025).
- Acetaminophen/ibuprofen combination tablets, 250 mg/125 mg (Glenmark) — manufacturing practice violations. Lots 17241302, 17241140, 17241141, all exp. July 2026 — sold on Amazon and Walmart, and should already be past date.

Prescription-strength generics:
- Dr. Reddy's IBU tablets (400, 600, and 800 mg) — multiple lots, failed impurity limits; a separate 600 mg 500-count bottle recall (lot C5406201) failed tablet specifications.
- Repackagers of Dr. Reddy's tablets — Direct Rx (800 mg ibuprofen, several bottle sizes) and Preferred Pharmaceuticals (400 mg, CA and NV only), both for failing impurity specifications.

Note: the 6 oldest matches weren't shown. If you have a specific bottle in mind, tell me the brand, strength, and lot number and I'll check it directly. If it matches any of these, stop using it and ask your pharmacist what to do — and if a child may have taken the Motrin syringe from the Class I recall, call poison control at 1-800-222-1222.

FDA data last updated November 18, 2026 — this isn't medical advice.

### Response 5 — "Has metformin from Teva ever been recalled?"
Yes — the FDA data shows 9 past recalls of Teva metformin products, all now listed as terminated (closed). None are ongoing. All were Class II.

2023 — NDMA impurity (extended-release 1000 mg)
- One lot of 60-count bottles (lot 1410946A, exp. 06/2023), shipped to California only
- Reason: levels of NDMA (a probable carcinogen) above the FDA's daily limit

2020 — NDMA impurity (extended-release 500 mg and 750 mg)
- Actavis-labeled bottles of 100 and 1,000 tablets, nationwide including Puerto Rico
- Affected lots expired between mid-2020 and late 2021
- Part of the wider 2020 metformin NDMA recalls across several manufacturers

2018 — possible missing laser drilling (extended-release tablets)
- Affected 500 mg, 1000 mg, Fortamet 1000 mg, and bulk pioglitazone/metformin product
- Some tablets may have lacked the laser-drilled hole that controls how the drug is released
- Affected lots expired between 2019 and 2020

2014 — testing procedures not followed
- Glyburide-metformin 5 mg/500 mg, lot TE36018 (exp. 06/2015)

Since every lot listed is long expired, none of these should be in a current prescription. If you're asking about a bottle you have now, the lot number and expiration date will settle it — tell me the lot and strength and I'll compare. Don't stop taking metformin on your own because of this history; if you have concerns, your pharmacist or prescriber can help.

FDA data last updated November 18, 2026 — this isn't medical advice.

### Response 6 — "Any recalls at my CVS?"
I can't check that, unfortunately. The FDA recall data names the company that recalled a product and the states it shipped to, but not which stores or pharmacies sold it — so there's no way to look up recalls for a specific CVS location.

What you can do instead:
- Tell me the products: If you list the medicines you have or take, I can check each one for recalls. Brand and manufacturer on the label help, since recalls often apply to one manufacturer's version rather than every version of a drug.
- Check lot numbers: If you have a bottle or box, give me the lot number and expiration date — recalls usually cover specific lots, so that settles it for that exact package.
- Ask the pharmacy: CVS pharmacists receive recall notices and can tell you whether a prescription you filled came from an affected lot. For prescriptions, calling the store is the most direct route.
- Check the FDA directly: The FDA posts current drug recalls on its drug recalls page at fda.gov.

If it's a prescription, the label usually shows the manufacturer, but the lot number often isn't on the pharmacy label — the pharmacy can look it up from their fill record.

This isn't medical advice.

### Response 7 — "Is Zorblex 50mg recalled?"
I found no recalls for "Zorblex" in the FDA data, current or past — and the search didn't match any product by that name at all, which suggests it may not be a drug in the FDA's records.

A few possibilities:
- Spelling: The name might be slightly different — check the bottle or the pharmacy printout.
- Brand vs. generic name: Try the active ingredient (it's usually printed below the brand name, often in smaller text or on the label). Searching on that can work better.
- Not US-marketed: The database only covers FDA-regulated drugs, so a product sold elsewhere or a supplement wouldn't appear.

Important: a search finding nothing doesn't mean the product is safe — and here, it doesn't tell me much either way. If you share the active ingredient, exact spelling, or manufacturer from the label, I'll run it again. A pharmacist can also identify the product from the label or NDC number.

This isn't medical advice.
