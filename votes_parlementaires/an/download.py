import urllib.request
from pathlib import Path

from votes_parlementaires.config import AN_LEGISLATURE_DEFAULT, an_raw_dir


def scrutins_url(legislature: int) -> str:
    return (
        f"https://data.assemblee-nationale.fr/static/openData/repository/"
        f"{legislature}/loi/scrutins/Scrutins.json.zip"
    )


def acteurs_url(legislature: int) -> str:
    return (
        f"https://data.assemblee-nationale.fr/static/openData/repository/"
        f"{legislature}/amo/deputes_actifs_mandats_actifs_organes_divises/"
        f"AMO40_deputes_actifs_mandats_actifs_organes_divises.json.zip"
    )


def acteurs_historique_url(legislature: int) -> str:
    # Couvre aussi les acteurs qui ont voté puis quitté leur mandat en cours
    # de législature (démission, décès, nomination au Gouvernement...),
    # absents du fichier "actifs" ci-dessus.
    return (
        f"https://data.assemblee-nationale.fr/static/openData/repository/"
        f"{legislature}/amo/tous_acteurs_mandats_organes_xi_legislature/"
        f"AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip"
    )


def scrutins_zip(legislature: int) -> Path:
    return an_raw_dir(legislature) / "Scrutins.json.zip"


def acteurs_zip(legislature: int) -> Path:
    return an_raw_dir(legislature) / "AMO40_deputes_actifs_mandats_actifs_organes_divises.json.zip"


def acteurs_historique_zip(legislature: int) -> Path:
    return (
        an_raw_dir(legislature)
        / "AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip"
    )


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    return dest


def download_scrutins(legislature: int = AN_LEGISLATURE_DEFAULT) -> Path:
    return _download(scrutins_url(legislature), scrutins_zip(legislature))


def download_acteurs(legislature: int = AN_LEGISLATURE_DEFAULT) -> Path:
    return _download(acteurs_url(legislature), acteurs_zip(legislature))


def download_acteurs_historique(legislature: int = AN_LEGISLATURE_DEFAULT) -> Path:
    return _download(acteurs_historique_url(legislature), acteurs_historique_zip(legislature))


if __name__ == "__main__":
    print("Downloading scrutins...")
    download_scrutins()
    print("Downloading acteurs/organes actifs...")
    download_acteurs()
    print("Downloading acteurs historique...")
    download_acteurs_historique()
    print("Done.")
