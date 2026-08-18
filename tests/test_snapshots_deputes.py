import html

from votes_parlementaires.an.taxonomy import CATEGORIES
from votes_parlementaires.snapshots.deputes import (
    GroupRegistry,
    categories_table_html,
    category_color_vars,
    category_tag_rules,
    fmt_date,
    party_color,
    slugify,
    to_roman,
)

MOIS_FULL = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def test_slugify():
    assert slugify("LFI-NFP") == "lfi-nfp"
    assert slugify("EcoS") == "ecos"
    assert slugify("Les Démocrates") == "les-d-mocrates"


def test_to_roman():
    assert to_roman(17) == "XVII"
    assert to_roman(1) == "I"
    assert to_roman(4) == "IV"
    assert to_roman(2026) == "MMXXVI"


def test_fmt_date_valid_iso():
    assert fmt_date("2026-08-18", MOIS_FULL) == "18 août 2026"


def test_fmt_date_invalid_returns_input():
    assert fmt_date("not-a-date", MOIS_FULL) == "not-a-date"
    assert fmt_date(None, MOIS_FULL) == ""


def test_party_color_known_group_is_stable():
    assert party_color("RN") == party_color("RN")
    assert party_color("EPR") != party_color("RN")


def test_party_color_unknown_group_is_deterministic():
    c1 = party_color("Un Nouveau Groupe Jamais Vu")
    c2 = party_color("Un Nouveau Groupe Jamais Vu")
    assert c1 == c2


def test_group_registry_groups_same_texte_together():
    groups = GroupRegistry(textes_by_key={}, categorie_map={})
    titre1 = "l'amendement n° 1 de M. X à l'article 3 du projet de loi de finances pour 2026."
    titre2 = "l'amendement n° 2 de Mme Y à l'article 4 du projet de loi de finances pour 2026."
    gi1, action1 = groups.get(titre1)
    gi2, action2 = groups.get(titre2)
    assert gi1 == gi2
    assert action1 != action2
    assert len(groups.groups) == 1


def test_group_registry_uses_categorie_map():
    key = "projet de loi de finances pour 2026"
    groups = GroupRegistry(
        textes_by_key={key: "projet de loi de finances pour 2026"},
        categorie_map={key: "finances_fiscalite"},
    )
    gi, _ = groups.get("l'ensemble du projet de loi de finances pour 2026.")
    assert groups.groups[gi] == ["projet de loi de finances pour 2026", "finances_fiscalite"]


def test_group_registry_unmatched_titles_share_fallback_group():
    groups = GroupRegistry(textes_by_key={}, categorie_map={})
    gi1, _ = groups.get("la demande de suspension de séance présentée par M. X.")
    gi2, _ = groups.get("la demande de suspension de séance présentée par M. Y.")
    assert gi1 == gi2
    assert groups.groups[gi1] == ["Autres scrutins", "autre"]


def test_categories_table_html_lists_every_category():
    out = categories_table_html()
    for c in CATEGORIES:
        assert c["id"] in out
        assert html.escape(c["label"]) in out


def test_category_color_vars_and_tag_rules_cover_every_category():
    vars_css = category_color_vars()
    rules_css = category_tag_rules()
    for c in CATEGORIES:
        assert f"--cat-{c['id']}: {c['color']};" in vars_css
        assert f".cat-tag.cat-{c['id']}" in rules_css
