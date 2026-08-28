import csv
from pathlib import Path

import pandas as pd

# Le CSV publié par le Sénat fait précéder l'en-tête réel d'un préambule de
# lignes commentées (requête SQL d'origine, nombre de lignes...), chacune
# commençant par "%". On les filtre plutôt que de sauter un nombre fixe de
# lignes, pour rester robuste si le préambule change de taille.
COLUMNS = {
    "Matricule": "senateur_ref",
    "Qualité": "civ",
    "Nom usuel": "nom",
    "Prénom usuel": "prenom",
    "État": "etat",
    "Groupe politique": "groupe_libelle",
    "Circonscription": "departement",
    "Commission permanente": "commission",
}


def load_senateurs(csv_path: Path) -> pd.DataFrame:
    """Sénateurs actuellement en mandat (etat == "ACTIF"), un par ligne."""
    with open(csv_path, encoding="latin-1", newline="") as f:
        lines = [line for line in f if not line.startswith("%")]
    reader = csv.DictReader(lines)
    rows = [
        {out: row.get(src) for src, out in COLUMNS.items()}
        for row in reader
        if row.get("État") == "ACTIF"
    ]
    return pd.DataFrame(rows, columns=list(COLUMNS.values()))
