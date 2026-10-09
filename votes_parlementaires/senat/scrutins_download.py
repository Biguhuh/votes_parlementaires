"""Téléchargement des pages de scrutins publics du Sénat.

Contrairement à l'Assemblée nationale, le Sénat ne publie pas d'archive
JSON/XML des scrutins : on scrape les pages HTML publiques, organisées par
année de session (ex: la session 2020-2021 est numérotée "2020"), chacune
listant les numéros de scrutin de cette session.
"""

import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from votes_parlementaires.config import senat_raw_dir

USER_AGENT = "Mozilla/5.0 (compatible; votes-parlementaires-bot)"

# senat.fr n'a pas d'API : on scrape des centaines/milliers de pages HTML
# d'affilée, sur lesquelles quelques échecs réseau transitoires (timeout TLS,
# reset...) sont attendus — on retente avant d'abandonner.
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 3


def session_url(annee: int) -> str:
    return f"https://www.senat.fr/scrutin-public/scr{annee}.html"


def scrutin_url(annee: int, numero: int) -> str:
    return f"https://www.senat.fr/scrutin-public/{annee}/scr{annee}-{numero}.html"


def fetch_bytes(url: str, timeout: int = 20) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            # Une erreur client (404...) ne se résout pas en réessayant.
            if 400 <= e.code < 500 or attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
        except (urllib.error.URLError, TimeoutError):
            if attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)


def fetch_html(url: str) -> str:
    return fetch_bytes(url).decode("utf-8")


def list_scrutin_numeros(annee: int) -> list[int]:
    """Numéros de tous les scrutins d'une session, en scrapant la page de
    session (qui liste un lien par scrutin). Liste vide si la session n'a pas
    encore de page : senat.fr ne la crée qu'au premier scrutin, donc la
    session qui démarre le 1er octobre renvoie 404 pendant quelques jours."""
    try:
        html = fetch_html(session_url(annee))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    pattern = re.compile(rf'href="{annee}/scr{annee}-(\d+)\.html"')
    numeros = sorted({int(m.group(1)) for m in pattern.finditer(html)})
    return numeros


def scrutin_html_path(annee: int, numero: int) -> Path:
    return senat_raw_dir() / "scrutins" / str(annee) / f"scr{annee}-{numero}.html"


def download_scrutin(annee: int, numero: int) -> Path:
    dest = scrutin_html_path(annee, numero)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(fetch_html(scrutin_url(annee, numero)), encoding="utf-8")
    return dest
