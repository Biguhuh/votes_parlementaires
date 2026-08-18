import re

from votes_parlementaires.an.taxonomy import CATEGORIES, CATEGORY_IDS, CATEGORY_LABELS

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def test_category_ids_are_unique():
    assert len(CATEGORY_IDS) == len(set(CATEGORY_IDS))


def test_autre_is_the_fallback_and_present():
    assert "autre" in CATEGORY_IDS


def test_every_category_has_required_fields():
    for c in CATEGORIES:
        assert c["id"] and c["id"] == c["id"].lower()
        assert c["label"]
        assert c["description"]
        assert HEX_COLOR.match(c["color"]), f"invalid color for {c['id']}: {c['color']}"


def test_category_labels_matches_categories():
    assert CATEGORY_LABELS == {c["id"]: c["label"] for c in CATEGORIES}
