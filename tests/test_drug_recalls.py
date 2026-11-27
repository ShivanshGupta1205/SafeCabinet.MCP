import json
from pathlib import Path

import safecabinet.tools.drug_recalls as drug_recalls
from safecabinet.openfda.errors import NotFoundError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    fixture_path = FIXTURES_DIR / f"drug_enforcement_{name}.json"
    with open(fixture_path, "r") as f:
        return json.loads(f.read())


def fake_get_returning(name: str, count_name: str | None = None, calls: list | None = None):
    """Fake openFDA: count requests get the count fixture, record searches get the records fixture.

    Pass a list as `calls` to record each request's `count` value (None for a record search).
    """
    def fake_get(*args, **kwargs):
        if calls is not None:
            calls.append(kwargs.get("count"))
        if kwargs.get("count"):
            return load_fixture(count_name or f"{name}_count")
        return load_fixture(name)
    return fake_get


def test_several_manufacturers_ask_which_one(monkeypatch):
    # Arrange: fake openFDA count returns 4 different Tylenol firms
    monkeypatch.setattr(drug_recalls, "get", fake_get_returning("tylenol"))

    # Act: call check_drug_recalls with no manufacturer
    result = drug_recalls.check_drug_recalls("tylenol")

    # Assert: it asks which manufacturer to use (4 firms + "Any manufacturer")
    question = result["needs_clarification"]
    assert question is not None
    assert len(question["options"]) == 5
    assert question["options"][-1] == drug_recalls.ANY_MANUFACTURER
    assert question["total_manufacturers"] == 4
    assert result["results"] == []
    assert result["match_count"] == 4


def test_one_manufacturer_no_question(monkeypatch):
    # Arrange: fake openFDA returns the metformin + Teva fixture (one firm)
    monkeypatch.setattr(drug_recalls, "get", fake_get_returning("metformin_teva"))

    # Act: call check_drug_recalls with a specific manufacturer
    result = drug_recalls.check_drug_recalls("metformin", manufacturer="Teva")

    # Assert: it answers directly, within the result cap
    assert result["needs_clarification"] is None
    assert 0 < len(result["results"]) <= drug_recalls.MAX_RESULTS
    assert result["match_count"] > 0


def test_not_found_never_says_safe(monkeypatch):
    # Arrange: fake openFDA raises NotFoundError (zero matches)
    def fake_get(*args, **kwargs):
        raise NotFoundError("no matches")

    monkeypatch.setattr(drug_recalls, "get", fake_get)

    # Act: call check_drug_recalls with a product that doesn't exist
    result = drug_recalls.check_drug_recalls("nonexistent product")

    # Assert: empty answer, but still warns that "not found" is not "safe"
    assert result["needs_clarification"] is None
    assert result["results"] == []
    assert result["match_count"] == 0
    assert any("does not mean the product is safe" in line for line in result["data_limitations"])


def test_sorting():
    # Arrange: handmade records, deliberately out of order
    records = [
        {"status": "Terminated", "classification": "Class I", "recall_initiation_date": "20240101"},
        {"status": "Ongoing", "classification": "Class II", "recall_initiation_date": "20200101"},
        {"status": "Ongoing", "classification": "Class II", "recall_initiation_date": "20250101"},
        {"status": "Completed", "classification": "Class II", "recall_initiation_date": "20260101"},
    ]

    # Act
    ordered = drug_recalls.sort_results(records)

    # Assert: Ongoing (newest first), then Completed, then Terminated.
    # Status beats class: a Terminated Class I still comes after anything active.
    assert [(r["status"], r["recall_initiation_date"]) for r in ordered] == [
        ("Ongoing", "20250101"),
        ("Ongoing", "20200101"),
        ("Completed", "20260101"),
        ("Terminated", "20240101"),
    ]


def test_class_one_beats_newer_milder_recalls():
    # Issue 1 from the 2026-11-27 Claude Desktop run: an older Class I must not be cut by the 10-result cap.
    records = [
        {"status": "Ongoing", "classification": "Class III", "recall_initiation_date": "20260901"},
        {"status": "Ongoing", "classification": "Class II", "recall_initiation_date": "20260801"},
        {"status": "Ongoing", "classification": "Class I", "recall_initiation_date": "20210101"},
    ]

    ordered = drug_recalls.sort_results(records)

    assert [r["classification"] for r in ordered] == ["Class I", "Class II", "Class III"]


def test_class_one_survives_the_cap(monkeypatch):
    # 11 newer Class III recalls + 1 old Class I: the Class I must be in the 10 shown
    records = [
        {"status": "Ongoing", "classification": "Class III", "recall_initiation_date": f"202609{day:02d}"}
        for day in range(1, 12)
    ] + [{"status": "Ongoing", "classification": "Class I", "recall_initiation_date": "20200101"}]
    response = {"meta": {"results": {"total": len(records)}, "last_updated": "2026-11-18"}, "results": records}
    monkeypatch.setattr(drug_recalls, "get", lambda *args, **kwargs: response)

    result = drug_recalls.check_drug_recalls("ibuprofen", all_manufacturers=True)

    assert len(result["results"]) == drug_recalls.MAX_RESULTS
    assert result["results"][0]["classification"] == "Class I"


def test_default_filter():
    search1 = drug_recalls.build_search("Tylenol", None, include_past=False)
    search2 = drug_recalls.build_search("Tylenol", None, include_past=True)
    assert 'status:"Ongoing"' in search1
    assert 'status:"Ongoing"' not in search2


def test_every_answer_carries_its_limits(monkeypatch):
    # D16: whatever path the tool takes, caveats and disclaimer must be present
    for fixture, manufacturer in [("tylenol", None), ("metformin_teva", "Teva")]:
        monkeypatch.setattr(drug_recalls, "get", fake_get_returning(fixture, count_name="tylenol_count"))

        result = drug_recalls.check_drug_recalls("any product", manufacturer=manufacturer)

        assert isinstance(result["data_limitations"], list)
        assert len(result["data_limitations"]) > 0
        assert result["disclaimer"]


def test_many_firms_capped_and_ranked(monkeypatch):
    # Arrange: acetaminophen has far more firms than we want to show
    monkeypatch.setattr(drug_recalls, "get", fake_get_returning("tylenol", count_name="acetaminophen_count"))

    # Act
    result = drug_recalls.check_drug_recalls("acetaminophen")

    # Assert: top MAX_OPTIONS firms + "Any manufacturer", ranked by recall count, real total reported
    question = result["needs_clarification"]
    assert len(question["options"]) == drug_recalls.MAX_OPTIONS + 1
    assert question["total_manufacturers"] > drug_recalls.MAX_OPTIONS
    assert question["options"][0] == "Ultra Seal Corporation"  # 44 recalls, the most in the fixture
    assert "If yours isn't listed" in question["question"]


def test_all_manufacturers_skips_question(monkeypatch):
    # Arrange: record which requests the tool makes
    calls = []
    monkeypatch.setattr(drug_recalls, "get", fake_get_returning("tylenol", calls=calls))

    # Act: the user said "any brand"
    result = drug_recalls.check_drug_recalls("tylenol", all_manufacturers=True)

    # Assert: no question, real results, and the count request was never made
    assert result["needs_clarification"] is None
    assert len(result["results"]) > 0
    assert calls == [None]
    assert result["query"]["all_manufacturers"] is True


def test_scope_line_present(monkeypatch):
    # The store/pharmacy limit must reach the user on every answer, even "nothing found"
    def fake_get(*args, **kwargs):
        raise NotFoundError("no matches")

    monkeypatch.setattr(drug_recalls, "get", fake_get)

    result = drug_recalls.check_drug_recalls("anything")

    assert any("stores or pharmacies" in line for line in result["data_limitations"])


def test_firm_counts_merges_same_firm():
    # Pure function: no fake needed
    terms = [
        {"term": "Teva Inc", "count": 3},
        {"term": "Pfizer", "count": 4},
        {"term": "TEVA", "count": 2},
    ]

    assert drug_recalls.firm_counts(terms) == [("Teva Inc", 5), ("Pfizer", 4)]


def test_build_search_without_product():
    # Clause list (D26): no dangling " AND " when a piece is missing
    assert drug_recalls.build_search("", "Teva", include_past=True) == 'recalling_firm:"Teva"'
