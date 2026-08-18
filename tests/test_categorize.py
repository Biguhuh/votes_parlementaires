from votes_parlementaires.an.categorize import (
    FALLBACK_CATEGORY,
    extract_texte,
    normalize_key,
    split_titre,
)
from votes_parlementaires.an.taxonomy import CATEGORY_IDS


def test_extract_texte_from_amendment_title():
    titre = (
        "l'amendement n° 948 de Mme Blin à l'article 17 (examen prioritaire) de la "
        "proposition de loi relative à l'accompagnement et aux soins palliatifs."
    )
    assert extract_texte(titre) == "proposition de loi relative à l'accompagnement et aux soins palliatifs"


def test_extract_texte_strips_reading_suffix():
    titre = "l'article 22 (examen prioritaire) du projet de loi de programmation pour la refondation de Mayotte (première lecture)."
    assert extract_texte(titre) == "projet de loi de programmation pour la refondation de Mayotte"


def test_extract_texte_strips_seconde_deliberation():
    titre = "l'ensemble du projet de loi de finances pour 2026 (seconde délibération)."
    assert extract_texte(titre) == "projet de loi de finances pour 2026"


def test_extract_texte_handles_resolution_europeenne():
    titre = (
        "l'amendement n° 7 de Mme Hamelet à l'article unique de la proposition de "
        "résolution européenne visant à refuser la ratification de l'accord."
    )
    texte = extract_texte(titre)
    assert texte is not None
    assert texte.startswith("proposition de résolution européenne")


def test_split_titre_returns_action_and_texte():
    titre = "l'ensemble de la proposition de loi visant à sortir la France du piège du narcotrafic (deuxième lecture)."
    action, texte = split_titre(titre)
    assert action == "l'ensemble"
    assert texte == "proposition de loi visant à sortir la France du piège du narcotrafic"


def test_split_titre_special_cases():
    assert split_titre("la motion de censure, déposée en application de l'article 49.")[1] == "motion de censure"
    assert split_titre("la déclaration du Gouvernement portant sur la stratégie de défense.")[1] == "déclaration du Gouvernement"


def test_split_titre_unmatched_returns_none_none():
    titre = "la demande de suspension de séance formulée par M. Boyard en application de l'article 58."
    assert split_titre(titre) == (None, None)


def test_extract_texte_non_string_returns_none():
    assert extract_texte(None) is None
    assert extract_texte(float("nan")) is None


def test_normalize_key_unifies_apostrophe_variants():
    a = normalize_key("proposition de loi relative au droit à l'aide à mourir")
    b = normalize_key("proposition de loi relative au droit à l’aide à mourir")
    assert a == b


def test_normalize_key_collapses_whitespace_and_case():
    assert normalize_key("  Projet   de Loi.  ") == "projet de loi"


def test_fallback_category_is_a_valid_category_id():
    assert FALLBACK_CATEGORY in CATEGORY_IDS
