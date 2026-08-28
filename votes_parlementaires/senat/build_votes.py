"""Télécharge et construit les scrutins publics + votes individuels du Sénat,
pour une ou plusieurs années de session (ex: 2025 = session 2025-2026).

Une session déjà complète (année révolue) ne change plus : ce script fusionne
donc son résultat avec les CSV déjà présents plutôt que de tout réécrire —
seules les années demandées via --annees sont (re)scrapées et remplacées.
Cela permet un run quotidien rapide (--annees <année en cours> uniquement)
qui laisse intact l'historique des années précédentes, déjà committé.

Usage :
    python -m votes_parlementaires.senat.build_votes --annees 2025
"""

import argparse
import csv
import time
from pathlib import Path

import pandas as pd

from votes_parlementaires.config import senat_processed_dir
from votes_parlementaires.senat.parse_scrutin import parse_scrutin_page
from votes_parlementaires.senat.session import current_session_annee
from votes_parlementaires.senat.scrutins_download import (
    download_scrutin,
    list_scrutin_numeros,
    scrutin_html_path,
)

SCRUTIN_FIELDS = [
    "scrutin_ref",
    "annee_session",
    "numero",
    "date_scrutin",
    "titre",
    "sort_libelle",
    "nombre_votants",
    "suffrages_exprimes",
    "decompte_pour",
    "decompte_contre",
    "decompte_abstentions",
    "decompte_non_votants",
]
VOTE_FIELDS = ["scrutin_ref", "senateur_ref", "position"]

# Pause entre deux requêtes vers senat.fr : il n'y a pas d'API dédiée, on
# scrape les pages HTML publiques, donc on reste poli avec leur serveur.
REQUEST_DELAY_SECONDS = 0.3


def scrutins_csv() -> Path:
    return senat_processed_dir() / "scrutins.csv"


def votes_csv() -> Path:
    return senat_processed_dir() / "votes.csv"


def senateurs_slugs_csv() -> Path:
    return senat_processed_dir() / "senateurs_slugs.csv"


def _fetch_scrutin_html(annee: int, numero: int, skip_download: bool) -> str:
    path = scrutin_html_path(annee, numero)
    if skip_download and path.exists():
        return path.read_text(encoding="utf-8")
    download_scrutin(annee, numero)
    time.sleep(REQUEST_DELAY_SECONDS)
    return path.read_text(encoding="utf-8")


def build_annee(annee: int, skip_download: bool, scrutin_writer, vote_writer, slugs: dict) -> int:
    numeros = list_scrutin_numeros(annee)
    print(f"Session {annee} : {len(numeros)} scrutins.")
    for i, numero in enumerate(numeros, start=1):
        html_text = _fetch_scrutin_html(annee, numero, skip_download)
        parsed = parse_scrutin_page(html_text, annee, numero)
        scrutin_writer.writerow(parsed["scrutin"])
        vote_writer.writerows(parsed["votes"])
        slugs.update(parsed["slugs"])
        if i % 50 == 0:
            print(f"  ...{i}/{len(numeros)} scrutins traités")
    return len(numeros)


def _load_existing(path: Path, dtype=None) -> pd.DataFrame | None:
    return pd.read_csv(path, dtype=dtype) if path.exists() else None


def main(annees: list[int], skip_download: bool = False) -> None:
    senat_processed_dir().mkdir(parents=True, exist_ok=True)
    annees_set = set(annees)

    tmp_scrutins = senat_processed_dir() / "scrutins.new.csv"
    tmp_votes = senat_processed_dir() / "votes.new.csv"
    slugs: dict[str, str] = {}

    with (
        open(tmp_scrutins, "w", newline="", encoding="utf-8") as sf,
        open(tmp_votes, "w", newline="", encoding="utf-8") as vf,
    ):
        scrutin_writer = csv.DictWriter(sf, fieldnames=SCRUTIN_FIELDS)
        vote_writer = csv.DictWriter(vf, fieldnames=VOTE_FIELDS)
        scrutin_writer.writeheader()
        vote_writer.writeheader()

        total = 0
        for annee in annees:
            total += build_annee(annee, skip_download, scrutin_writer, vote_writer, slugs)

    fresh_scrutins = pd.read_csv(tmp_scrutins)
    fresh_votes = pd.read_csv(tmp_votes)
    tmp_scrutins.unlink()
    tmp_votes.unlink()

    previous_scrutins = _load_existing(scrutins_csv())
    previous_votes = _load_existing(votes_csv())

    if previous_scrutins is not None:
        kept_scrutins = previous_scrutins[~previous_scrutins["annee_session"].isin(annees_set)]
        fresh_scrutins = pd.concat([kept_scrutins, fresh_scrutins], ignore_index=True)
    if previous_votes is not None:
        fresh_refs = set(fresh_scrutins.loc[fresh_scrutins["annee_session"].isin(annees_set), "scrutin_ref"])
        kept_votes = previous_votes[~previous_votes["scrutin_ref"].isin(fresh_refs)]
        fresh_votes = pd.concat([kept_votes, fresh_votes], ignore_index=True)

    fresh_scrutins = fresh_scrutins.sort_values(["annee_session", "numero"])
    fresh_scrutins.to_csv(scrutins_csv(), index=False)
    fresh_votes.to_csv(votes_csv(), index=False)

    if senateurs_slugs_csv().exists():
        previous_slugs = dict(pd.read_csv(senateurs_slugs_csv()).itertuples(index=False, name=None))
        previous_slugs.update(slugs)
        slugs = previous_slugs
    pd.DataFrame(sorted(slugs.items()), columns=["senateur_ref", "slug"]).to_csv(
        senateurs_slugs_csv(), index=False
    )

    print(f"Terminé : {total} scrutins (re)scrapés pour {sorted(annees_set)}, {len(fresh_scrutins)} au total.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Télécharge et construit les scrutins publics + votes individuels du Sénat."
    )
    parser.add_argument(
        "--annees",
        nargs="+",
        type=int,
        default=[current_session_annee()],
        help="Années de session à (re)scraper (ex: 2024 2025). Une session couvre octobre à septembre. "
        "Par défaut, seulement la session en cours. Les autres années déjà présentes dans les CSV "
        "existants sont conservées telles quelles.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Réutiliser les pages HTML déjà présentes en cache au lieu de les retélécharger.",
    )
    args = parser.parse_args()
    main(annees=args.annees, skip_download=args.skip_download)
