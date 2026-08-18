import argparse
import csv
from pathlib import Path

import pandas as pd

from votes_parlementaires.an.download import (
    acteurs_historique_zip,
    acteurs_zip,
    download_acteurs,
    download_acteurs_historique,
    download_scrutins,
    scrutins_zip,
)
from votes_parlementaires.an.legislature import detect_current_legislature
from votes_parlementaires.an.meta import write_build_meta
from votes_parlementaires.an.parse import (
    iter_scrutins,
    load_acteurs,
    load_organes,
    scrutin_record,
    vote_records,
)
from votes_parlementaires.config import an_processed_dir, an_raw_dir

SCRUTIN_FIELDS = [
    "scrutin_uid",
    "numero",
    "legislature",
    "organe_voteur_ref",
    "date_scrutin",
    "type_vote_code",
    "type_vote_libelle",
    "sort_code",
    "sort_libelle",
    "titre",
    "demandeur",
    "nombre_votants",
    "suffrages_exprimes",
    "suffrages_requis",
    "decompte_pour",
    "decompte_contre",
    "decompte_abstentions",
    "decompte_non_votants",
]
VOTE_FIELDS = [
    "scrutin_uid",
    "groupe_organe_ref",
    "acteur_ref",
    "mandat_ref",
    "position",
    "par_delegation",
]


def scrutins_csv(legislature: int) -> Path:
    return an_processed_dir(legislature) / "scrutins.csv"


def votes_csv(legislature: int) -> Path:
    return an_processed_dir(legislature) / "votes.csv"


def acteurs_csv(legislature: int) -> Path:
    return an_processed_dir(legislature) / "acteurs.csv"


def organes_csv(legislature: int) -> Path:
    return an_processed_dir(legislature) / "organes.csv"


def ensure_paths(legislature: int) -> None:
    an_raw_dir(legislature).mkdir(parents=True, exist_ok=True)
    an_processed_dir(legislature).mkdir(parents=True, exist_ok=True)


def build_scrutins_and_votes(legislature: int) -> None:
    with (
        open(scrutins_csv(legislature), "w", newline="", encoding="utf-8") as sf,
        open(votes_csv(legislature), "w", newline="", encoding="utf-8") as vf,
    ):
        scrutin_writer = csv.DictWriter(sf, fieldnames=SCRUTIN_FIELDS)
        vote_writer = csv.DictWriter(vf, fieldnames=VOTE_FIELDS)
        scrutin_writer.writeheader()
        vote_writer.writeheader()

        count = 0
        for scrutin in iter_scrutins(scrutins_zip(legislature)):
            scrutin_writer.writerow(scrutin_record(scrutin))
            vote_writer.writerows(vote_records(scrutin))
            count += 1
            if count % 1000 == 0:
                print(f"  ...{count} scrutins traités")
        print(f"Total: {count} scrutins traités")


def build_acteurs_and_organes(legislature: int) -> None:
    # Priorité aux acteurs/organes actifs (données les plus à jour), puis on
    # comble avec l'historique pour les acteurs ayant quitté leur mandat
    # (démission, décès, nomination au Gouvernement...) en cours de législature.
    acteurs = pd.concat(
        [
            load_acteurs(acteurs_zip(legislature)),
            load_acteurs(acteurs_historique_zip(legislature)),
        ]
    ).drop_duplicates(subset="acteur_ref", keep="first")
    organes = pd.concat(
        [
            load_organes(acteurs_zip(legislature)),
            load_organes(acteurs_historique_zip(legislature)),
        ]
    ).drop_duplicates(subset="organe_ref", keep="first")

    acteurs.to_csv(acteurs_csv(legislature), index=False)
    organes.to_csv(organes_csv(legislature), index=False)


def main(legislature: int | None = None, skip_download: bool = False) -> None:
    if legislature is None:
        print("Détection de la législature en cours...")
        legislature = detect_current_legislature()
    print(f"Législature : {legislature}")

    ensure_paths(legislature)

    if skip_download:
        print("Téléchargement ignoré (--skip-download), reconstruction à partir des fichiers déjà présents.")
    else:
        print("Téléchargement des scrutins...")
        download_scrutins(legislature)
        print("Téléchargement des acteurs/organes actifs...")
        download_acteurs(legislature)
        print("Téléchargement des acteurs historique...")
        download_acteurs_historique(legislature)

    print("Construction scrutins.csv / votes.csv...")
    build_scrutins_and_votes(legislature)

    print("Construction acteurs.csv / organes.csv...")
    build_acteurs_and_organes(legislature)

    write_build_meta(legislature)

    print("Terminé.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Télécharge et construit les données de votes AN.")
    parser.add_argument(
        "--legislature",
        type=int,
        default=None,
        help="Forcer un numéro de législature au lieu de le détecter automatiquement.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Ne pas retélécharger les sources, juste reconstruire les CSV à partir des zips déjà présents.",
    )
    args = parser.parse_args()
    main(legislature=args.legislature, skip_download=args.skip_download)
