"""Détecte la législature en cours en sondant le portail open data de
l'Assemblée nationale, plutôt que de se fier à une constante codée en dur.

Le jeu de données "députés actifs" existe dès la mise en place d'une nouvelle
législature (avant même le premier scrutin), c'est donc le plus fiable à
sonder pour savoir si une législature N+1 a démarré.
"""

import urllib.error
import urllib.request

from votes_parlementaires.config import AN_LEGISLATURE_DEFAULT


def deputes_actifs_url(legislature: int) -> str:
    return (
        f"https://data.assemblee-nationale.fr/static/openData/repository/"
        f"{legislature}/amo/deputes_actifs_mandats_actifs_organes_divises/"
        f"AMO40_deputes_actifs_mandats_actifs_organes_divises.json.zip"
    )


def _url_exists(url: str, timeout: int = 10) -> bool:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def detect_current_legislature(start: int = AN_LEGISLATURE_DEFAULT, max_ahead: int = 5) -> int:
    """Renvoie le numéro de la législature en cours.

    Part de `start` (la dernière législature connue) et avance tant que le
    jeu de données existe pour la législature suivante. Si `start` lui-même
    n'est pas joignable (pas de réseau, portail indisponible), on retombe
    silencieusement sur `start`.
    """
    if not _url_exists(deputes_actifs_url(start)):
        return start

    current = start
    for candidate in range(start + 1, start + 1 + max_ahead):
        if _url_exists(deputes_actifs_url(candidate)):
            current = candidate
        else:
            break
    return current


if __name__ == "__main__":
    print(detect_current_legislature())
