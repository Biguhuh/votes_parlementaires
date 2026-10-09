"""Construit, pour chaque sénateur·rice, la date de début de son service
continu (`depuis` : sa première élection) et celle de son mandat en cours
(`derniere_election`). La participation est comptée depuis `depuis`, pour
qu'une réélection ne fasse pas disparaître l'historique de vote — voir
senat/parse_mandat.py.

Nécessite que senateurs.csv et senateurs_slugs.csv existent déjà (voir
senat/build.py et senat/build_votes.py) : ce dernier fournit l'URL de la
fiche de chaque sénateur·rice, glanée gratuitement lors du scraping des
scrutins (chaque scrutin y renvoie les sénateur·rice·s qui y ont pris part).

Usage :
    python -m votes_parlementaires.senat.build_mandats
"""

import argparse
import time
from datetime import date
from pathlib import Path

import pandas as pd

from votes_parlementaires.config import senat_processed_dir
from votes_parlementaires.senat.build import senateurs_csv
from votes_parlementaires.senat.build_votes import senateurs_slugs_csv
from votes_parlementaires.senat.parse_mandat import parse_elections
from votes_parlementaires.senat.senateur_download import download_senateur_page, senateur_html_path

REQUEST_DELAY_SECONDS = 0.3
MANDAT_ANNEES = 6


def mandats_csv() -> Path:
    return senat_processed_dir() / "mandats.csv"


def _mandat_expire(depuis) -> bool:
    """Une date de début de mandat déjà connue reste valable jusqu'à la fin
    du mandat (6 ans) : au-delà, le/la sénateur·rice a forcément été
    réélu·e (ou la date est absente) et il faut relire sa fiche."""
    if not isinstance(depuis, str):
        return True
    debut = date.fromisoformat(depuis)
    return debut.replace(year=debut.year + MANDAT_ANNEES) <= date.today()


def _fetch_senateur_html(slug: str, skip_download: bool) -> str:
    path = senateur_html_path(slug)
    if skip_download and path.exists():
        return path.read_text(encoding="utf-8")
    download_senateur_page(slug)
    time.sleep(REQUEST_DELAY_SECONDS)
    return path.read_text(encoding="utf-8")


def main(skip_download: bool = False, refresh: bool = False) -> None:
    senateurs = pd.read_csv(senateurs_csv())
    slugs_path = senateurs_slugs_csv()
    if not slugs_path.exists():
        raise SystemExit(
            f"{slugs_path} introuvable : lance d'abord senat.build_votes pour glaner les URLs de fiches."
        )
    slugs = dict(pd.read_csv(slugs_path).itertuples(index=False, name=None))

    previous = None
    if mandats_csv().exists() and not refresh:
        known = pd.read_csv(mandats_csv())
        # Ancien format (une seule colonne `depuis`) : tout est à relire.
        if "derniere_election" in known.columns:
            previous = known.set_index("senateur_ref").to_dict("index")

    rows = []
    missing_slug = []
    for i, ref in enumerate(senateurs["senateur_ref"], start=1):
        if previous is not None and ref in previous and not _mandat_expire(previous[ref]["derniere_election"]):
            rows.append({"senateur_ref": ref, **previous[ref]})
            continue
        slug = slugs.get(ref)
        if slug is None:
            missing_slug.append(ref)
            continue
        html_text = _fetch_senateur_html(slug, skip_download)
        elections = parse_elections(html_text)
        # `depuis` : début du service continu (première élection listée) ;
        # `derniere_election` : début du mandat en cours, qui sert à savoir
        # quand relire la fiche (réélection).
        rows.append(
            {
                "senateur_ref": ref,
                "depuis": elections[0] if elections else None,
                "derniere_election": elections[-1] if elections else None,
            }
        )
        if i % 50 == 0:
            print(f"  ...{i}/{len(senateurs)} sénateur·rice·s traité·e·s")

    if missing_slug:
        print(
            f"{len(missing_slug)} sénateur·rice·s sans fiche connue (jamais apparu·e·s dans un scrutin scrapé) : "
            f"{', '.join(missing_slug)}"
        )

    pd.DataFrame(rows).to_csv(mandats_csv(), index=False)
    print(f"Terminé : {len(rows)} dates de mandat écrites dans {mandats_csv()}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Construit la date de début de mandat de chaque sénateur·rice actif·ve."
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Réutiliser les pages HTML déjà présentes en cache au lieu de les retélécharger.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Reconstruire aussi les dates déjà connues (par défaut, on ne refetch que les nouvelles/manquantes).",
    )
    args = parser.parse_args()
    main(skip_download=args.skip_download, refresh=args.refresh)
