from pathlib import Path

from votes_parlementaires.config import senat_raw_dir
from votes_parlementaires.senat.scrutins_download import fetch_bytes

# Export global des sénateurs (actifs et anciens), publié par l'open data du
# Sénat (data.senat.fr/les-senateurs/). Encodé en latin-1, avec un préambule
# de lignes commentées (`%...`) avant l'en-tête CSV — voir senat/parse.py.
SENATEURS_URL = "https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv"

# data.senat.fr est parfois injoignable depuis les runners GitHub : sans
# timeout explicite, l'attente dure ~2 min (timeout TCP du système) par essai.
DOWNLOAD_TIMEOUT_SECONDS = 30


def senateurs_csv_raw() -> Path:
    return senat_raw_dir() / "ODSEN_GENERAL.csv"


def download_senateurs() -> Path:
    dest = senateurs_csv_raw()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(fetch_bytes(SENATEURS_URL, timeout=DOWNLOAD_TIMEOUT_SECONDS))
    return dest


if __name__ == "__main__":
    print("Téléchargement de la liste des sénateurs...")
    download_senateurs()
    print("Terminé.")
