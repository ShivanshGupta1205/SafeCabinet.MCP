import re
from datetime import date, timedelta
from safecabinet.openfda.client import get
from safecabinet.openfda.errors import NotFoundError

SOURCE = "openFDA /drug/enforcement"
FETCH_LIMIT = 100
MAX_RESULTS = 10
MAX_OPTIONS = 8
COUNT_LIMIT = 1000
ANY_MANUFACTURER = "Any manufacturer" 
RECENT_DAYS = 183
STATUS_RANK = {"Ongoing": 0, "Completed": 1, "Terminated": 2}
CLASS_RANK = {"Class I": 0, "Class II": 1, "Class III": 2}
FIRM_SUFFIXES = {"inc", "llc", "ltd", "limited", "corp", "corporation", "co", "company", "lp", "plc"}

# ----------------- helper functions -----------------

def new_envelope(
    product: str,
    manufacturer: str | None,
    lot_number: str | None,
    include_past: bool,
    all_manufacturers: bool,
) -> dict:
    return {
        "query": {
            "product": product,
            "manufacturer": manufacturer,
            "lot_number": lot_number,
            "include_past": include_past,
            "all_manufacturers": all_manufacturers,
        },
        "results": [],
        "match_count": 0,
        "source": SOURCE,
        "data_last_updated": None,
        "data_limitations": [
            "No recall found does not mean the product is safe.",
            "Lot numbers are not checked automatically. Compare your lot with each result's code_info.",
            "FDA recall data names the company that recalled the product and the states it was shipped to. "
            "It does not show which stores or pharmacies sold it.",
        ],
        "disclaimer": "Not medical advice. For educational purposes only. Please consult a pharmacist or doctor about your medicine.",
        "needs_clarification": None,
    }


def build_search(product: str, manufacturer: str | None, include_past: bool) -> str:
    clauses = []
    if product:
        clauses.append(f'product_description:"{product}"')
    if manufacturer:
        clauses.append(f'recalling_firm:"{manufacturer}"')
    if not include_past:
        start = (date.today() - timedelta(days=RECENT_DAYS)).strftime("%Y%m%d")
        end = date.today().strftime("%Y%m%d")
        # Old recalls can still be Ongoing, so a date window alone would hide active ones.
        clauses.append(f'(status:"Ongoing" OR recall_initiation_date:[{start} TO {end}])')
    return " AND ".join(clauses)


def normalize_firm(name: str) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    return " ".join(w for w in words if w not in FIRM_SUFFIXES)


def firm_counts(terms: list[dict]) -> list[tuple[str, int]]:
    names: dict[str, str] = {}  # normalized -> name as written
    totals: dict[str, int] = {}  # normalized -> summed count
    for t in terms:
        key = normalize_firm(t["term"])
        names.setdefault(key, t["term"])
        totals[key] = totals.get(key, 0) + t["count"]
    return sorted(((names[k], totals[k]) for k in totals), key=lambda x: x[1], reverse=True)


def manufacturer_question(firms: list[tuple[str, int]]) -> dict:
    shown = [name for name, _ in firms[:MAX_OPTIONS]]
    question = "Several manufacturers have recalls for this product. Which manufacturer's information do you want?"
    if len(firms) > MAX_OPTIONS:
        question += (
            f" Showing the {MAX_OPTIONS} of {len(firms)} manufacturers with the most recalls."
            " If yours isn't listed, say its name."
        )
    return {
        "question": question,
        "options": shown + [ANY_MANUFACTURER],
        "total_manufacturers": len(firms),
    }


def sort_results(results: list[dict]) -> list[dict]:
    newest_first = sorted(results, key=lambda r: r.get("recall_initiation_date") or "", reverse=True)
    return sorted(
        newest_first,
        key=lambda r: (STATUS_RANK.get(r.get("status") or "", 3), CLASS_RANK.get(r.get("classification") or "", 3)),
    )


def cleaned_results(records: list[dict]) -> list[dict]:
    return [
        {
            "status": r.get("status"),
            "classification": r.get("classification"),
            "recalling_firm": r.get("recalling_firm"),
            "product_description": r.get("product_description"),
            "reason_for_recall": r.get("reason_for_recall"),
            "recall_initiation_date": r.get("recall_initiation_date"),
            "recall_number": r.get("recall_number"),
            "distribution_pattern": r.get("distribution_pattern"),
            "code_info": r.get("code_info"),
        }
        for r in records
    ]


# ----------------- main function -----------------

def check_drug_recalls(
    product: str,
    manufacturer: str | None = None,
    lot_number: str | None = None,
    include_past: bool = False,
    all_manufacturers: bool = False, 
) -> dict:
    """Look up FDA drug recalls for a product. By default only active or recent recalls."""
    result = new_envelope(product, manufacturer, lot_number, include_past, all_manufacturers)
    if not include_past:
        result["data_limitations"].append(
            "Only recalls that are still ongoing or started in the last 6 months are shown. "
            "Use include_past=True for older, finished recalls."
        )

    # Step 1: no manufacturer and not "any" -> count firms across ALL matches and ask if several.
    if not manufacturer and not all_manufacturers:
        try:
            counted = get(
                "drug/enforcement",
                build_search(product, None, include_past),
                limit=COUNT_LIMIT,
                count="recalling_firm.exact",
            )
        except NotFoundError:
            return result  # zero matches: no need for a second request
        firms = firm_counts(counted.get("results", []))
        if len(firms) > 1:
            result["match_count"] = sum(count for _, count in firms)
            result["data_last_updated"] = counted.get("meta", {}).get("last_updated")
            result["data_limitations"].append(f"Data reflects FDA reports as of {result['data_last_updated']}.")
            result["needs_clarification"] = manufacturer_question(firms)
            return result
        # Exactly one firm: nothing to ask, fall through to the normal search.

    # Step 2: the normal records search.
    try:
        response = get("drug/enforcement", build_search(product, manufacturer, include_past), limit=FETCH_LIMIT)
    except NotFoundError:
        return result

    meta = response.get("meta", {})
    records = response.get("results", [])
    result["match_count"] = meta.get("results", {}).get("total", len(records))
    result["data_last_updated"] = meta.get("last_updated")
    result["data_limitations"].append(f"Data reflects FDA reports as of {result['data_last_updated']}.")

    shown = sort_results(cleaned_results(records))[:MAX_RESULTS]
    result["results"] = shown
    if result["match_count"] > len(shown):
        result["data_limitations"].append(
            f"Showing {len(shown)} of {result['match_count']} matching recalls: active first, then most serious class, then newest."
        )
    return result
