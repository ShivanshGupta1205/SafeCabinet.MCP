import re
from datetime import date, timedelta
from safecabinet.openfda.client import get
from safecabinet.openfda.errors import NotFoundError

SOURCE = "openFDA /drug/enforcement"
FETCH_LIMIT = 100
MAX_RESULTS = 10
RECENT_DAYS = 183
STATUS_RANK = {"Ongoing": 0, "Completed": 1, "Terminated": 2}
FIRM_SUFFIXES = {"inc", "llc", "ltd", "limited", "corp", "corporation", "co", "company", "lp", "plc"}


def new_envelope(product: str, manufacturer: str | None, lot_number: str | None, include_past: bool) -> dict:
    return {
        "query": {
            "product": product,
            "manufacturer": manufacturer,
            "lot_number": lot_number,
            "include_past": include_past,
        },
        "results": [],
        "match_count": 0,
        "source": SOURCE,
        "data_last_updated": None,
        "data_limitations": [
            "No recall found does not mean the product is safe.",
            "Lot numbers are not checked automatically. Compare your lot with each result's code_info.",
        ],
        "disclaimer": "Not medical advice. For educational purposes only. Please consult a pharmacist or doctor about your medicine.",
        "needs_clarification": None,
    }


def build_search(product: str, manufacturer: str | None, include_past: bool) -> str:
    search = f'product_description:"{product}"'
    if manufacturer:
        search += f' AND recalling_firm:"{manufacturer}"'
    if not include_past:
        # Old recalls can still be Ongoing, so a date window alone would hide active ones.
        start = (date.today() - timedelta(days=RECENT_DAYS)).strftime("%Y%m%d")
        end = date.today().strftime("%Y%m%d")
        search += f' AND (status:"Ongoing" OR recall_initiation_date:[{start} TO {end}])'
    return search


def normalize_firm(name: str) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    return " ".join(w for w in words if w not in FIRM_SUFFIXES)


def distinct_firms(records: list[dict]) -> list[str]:
    firms = {}
    for record in records:
        name = record.get("recalling_firm") or ""
        firms.setdefault(normalize_firm(name), name)
    return sorted(firms.values())


def sort_results(results: list[dict]) -> list[dict]:
    newest_first = sorted(results, key=lambda r: r.get("recall_initiation_date") or "", reverse=True)
    return sorted(newest_first, key=lambda r: STATUS_RANK.get(r.get("status") or "", 3))


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


def check_drug_recalls(product: str, manufacturer: str | None = None, lot_number: str | None = None, include_past: bool = False) -> dict:
    """Look up FDA drug recalls for a product. By default only active or recent recalls."""
    result = new_envelope(product, manufacturer, lot_number, include_past)
    if not include_past:
        result["data_limitations"].append(
            "Only recalls that are still ongoing or started in the last 6 months are shown. "
            "Use include_past=True for older, finished recalls."
        )

    try:
        response = get("drug/enforcement", build_search(product, manufacturer, include_past), limit=FETCH_LIMIT)
    except NotFoundError:
        return result

    meta = response.get("meta", {})
    records = response.get("results", [])
    result["match_count"] = meta.get("results", {}).get("total", len(records))
    result["data_last_updated"] = meta.get("last_updated")
    result["data_limitations"].append(f"Data reflects FDA reports as of {result['data_last_updated']}.")

    if not manufacturer:
        firms = distinct_firms(records)
        if len(firms) > 1:
            result["needs_clarification"] = {
                "question": "Several manufacturers have recalls for this product. Which manufacturer's information do you want?",
                "options": firms,
            }
            return result

    shown = sort_results(cleaned_results(records))[:MAX_RESULTS]
    result["results"] = shown
    if result["match_count"] > len(shown):
        result["data_limitations"].append(
            f"Showing {len(shown)} of {result['match_count']} matching recalls, active and newest first."
        )
    return result
