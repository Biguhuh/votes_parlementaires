from pathlib import Path

from votes_parlementaires.config import senat_raw_dir
from votes_parlementaires.senat.scrutins_download import fetch_html


def senateur_url(slug: str) -> str:
    return f"https://www.senat.fr/senateur/{slug}.html"


def senateur_html_path(slug: str) -> Path:
    return senat_raw_dir() / "senateurs" / f"{slug}.html"


def download_senateur_page(slug: str) -> Path:
    dest = senateur_html_path(slug)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(fetch_html(senateur_url(slug)), encoding="utf-8")
    return dest
