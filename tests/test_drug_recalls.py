import json
from pathlib import Path

import safecabinet.tools.drug_recalls as drug_recalls
from safecabinet.openfda.errors import NotFoundError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    fixture_path = FIXTURES_DIR / f"drug_enforcement_{name}.json"
    with open(fixture_path, "r") as f:
        return json.loads(f.read())


def fake_get_returning(name: str):
    return lambda *args, **kwargs: load_fixture(name)


def test_several_manufacturers_ask_which_one(monkeypatch):
    # Arrange: fake openFDA returns the Tylenol fixture (4 different firms)
    monkeypatch.setattr(drug_recalls, "get", fake_get_returning("tylenol"))

    # Act: call check_drug_recalls with no manufacturer
    result = drug_recalls.check_drug_recalls("tylenol")

    # Assert: it asks which manufacturer to use
    assert result["needs_clarification"] is not None
    assert len(result["needs_clarification"]["options"]) == 4
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
        {"status": "Terminated", "recall_initiation_date": "20240101"},
        {"status": "Ongoing", "recall_initiation_date": "20200101"},
        {"status": "Ongoing", "recall_initiation_date": "20250101"},
        {"status": "Completed", "recall_initiation_date": "20260101"},
    ]

    # Act
    ordered = drug_recalls.sort_results(records)

    # Assert: Ongoing (newest first), then Completed, then Terminated
    assert [(r["status"], r["recall_initiation_date"]) for r in ordered] == [
        ("Ongoing", "20250101"),
        ("Ongoing", "20200101"),
        ("Completed", "20260101"),
        ("Terminated", "20240101"),
    ]


def test_default_filter():
    search1 = drug_recalls.build_search("Tylenol", None, include_past=False)
    search2 = drug_recalls.build_search("Tylenol", None, include_past=True)
    assert 'status:"Ongoing"' in search1
    assert 'status:"Ongoing"' not in search2


def test_every_answer_carries_its_limits(monkeypatch):
    # D16: whatever path the tool takes, caveats and disclaimer must be present
    for fixture, manufacturer in [("tylenol", None), ("metformin_teva", "Teva")]:
        monkeypatch.setattr(drug_recalls, "get", fake_get_returning(fixture))

        result = drug_recalls.check_drug_recalls("any product", manufacturer=manufacturer)

        assert isinstance(result["data_limitations"], list)
        assert len(result["data_limitations"]) > 0
        assert result["disclaimer"]
