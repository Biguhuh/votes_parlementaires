import urllib.request
from pathlib import Path

from votes_parlementaires.config import senat_raw_dir

# Export global des sénateurs (actifs et anciens), publié par l'open data du
# Sénat (data.senat.fr/les-senateurs/). Encodé en latin-1, avec un préambule
# de lignes commentées (`%...`) avant l'en-tête CSV — voir senat/parse.py.
SENATEURS_URL = "https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv"


def senateurs_csv_raw() -> Path:
    return senat_raw_dir() / "ODSEN_GENERAL.csv"


def download_senateurs() -> Path:
    dest = senateurs_csv_raw()
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(SENATEURS_URL, dest)
    return dest


if __name__ == "__main__":
    print("Téléchargement de la liste des sénateurs...")
    download_senateurs()
    print("Terminé.")
