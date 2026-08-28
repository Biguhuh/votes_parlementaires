"""Télécharge et construit la liste des sénateurs actifs.

Usage :
    python -m votes_parlementaires.senat.build
"""

import argparse
from pathlib import Path

from votes_parlementaires.an.legislature import detect_current_legislature
from votes_parlementaires.config import senat_processed_dir, senat_raw_dir
from votes_parlementaires.senat.departements import load_departement_codes, normalize_nom
from votes_parlementaires.senat.download import download_senateurs, senateurs_csv_raw
from votes_parlementaires.senat.parse import load_senateurs


def senateurs_csv() -> Path:
    return senat_processed_dir() / "senateurs.csv"


def main(skip_download: bool = False, legislature: int | None = None) -> None:
    senat_raw_dir().mkdir(parents=True, exist_ok=True)
    senat_processed_dir().mkdir(parents=True, exist_ok=True)

    if skip_download:
        print("Téléchargement ignoré (--skip-download), reconstruction à partir du fichier déjà présent.")
    else:
        print("Téléchargement de la liste des sénateurs...")
        download_senateurs()

    print("Construction senateurs.csv...")
    df = load_senateurs(senateurs_csv_raw())

    legislature = legislature or detect_current_legislature()
    codes = load_departement_codes(legislature)
    lookup = df["departement"].map(
        lambda nom: codes.get(normalize_nom(nom)) if isinstance(nom, str) else None
    )
    df["num_departement"] = lookup.map(lambda t: t[0] if t else None)
    df["region"] = lookup.map(lambda t: t[1] if t else None)

    df.to_csv(senateurs_csv(), index=False)
    print(f"{len(df)} sénateurs actifs ({df['num_departement'].notna().sum()} avec code département résolu).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Télécharge et construit la liste des sénateurs actifs.")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Ne pas retélécharger la source, juste reconstruire le CSV à partir du fichier déjà présent.",
    )
    parser.add_argument(
        "--legislature",
        type=int,
        default=None,
        help="Législature AN à utiliser pour résoudre les codes département (par défaut : détectée automatiquement).",
    )
    args = parser.parse_args()
    main(skip_download=args.skip_download, legislature=args.legislature)
