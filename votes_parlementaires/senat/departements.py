"""L'export sénateurs (ODSEN_GENERAL.csv) donne le nom de département de
chaque sénateur·rice ("Circonscription") mais pas son code numérique — on le
retrouve en le recoupant avec les données déjà connues côté Assemblée
nationale, qui référencent les mêmes départements officiels (le code INSEE
d'un département ne dépend pas de la chambre)."""

import re
import unicodedata

import pandas as pd

from votes_parlementaires.config import an_processed_dir


def normalize_nom(nom: str) -> str:
    ascii_nom = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", ascii_nom.lower())


def load_departement_codes(legislature: int) -> dict[str, tuple[str, str]]:
    """{nom de département normalisé: (code, région)}."""
    acteurs = pd.read_csv(an_processed_dir(legislature) / "acteurs.csv")
    pairs = (
        acteurs[["departement", "num_departement", "region"]]
        .dropna(subset=["departement", "num_departement"])
        .drop_duplicates(subset="departement")
    )
    return {normalize_nom(row.departement): (row.num_departement, row.region) for row in pairs.itertuples()}
