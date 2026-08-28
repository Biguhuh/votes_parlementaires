import re

from bs4 import BeautifulSoup

MOIS = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}
# Ex: "Réélue le 27 septembre 2020" ou "Elu le 21 septembre 2008".
ELECTION_RE = re.compile(r"(?:ré)?[eé]lue?\s+le\s+(\d{1,2})(?:er)?\s+(\w+)\s+(\d{4})", re.IGNORECASE)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_mandat_debut(html_text: str) -> str | None:
    """Date (ISO) du début du mandat sénatorial en cours : la plus récente
    des dates "Elu(e) le ..." / "Réélu(e) le ..." listées dans le bloc
    "Mandat sénatorial" de la fiche du/de la sénateur·rice sur senat.fr."""
    soup = BeautifulSoup(html_text, "html.parser")
    heading = soup.find(lambda tag: tag.name in ("h3", "h4") and "Mandat sénatorial" in tag.get_text())
    if heading is None:
        return None
    block = heading.find_next_sibling("p")
    if block is None:
        return None

    dates = []
    for m in ELECTION_RE.finditer(_clean(block.get_text(" ", strip=True))):
        jour, mois_nom, annee = m.groups()
        mois = MOIS.get(mois_nom.lower())
        if mois is None:
            continue
        dates.append(f"{annee}-{mois:02d}-{int(jour):02d}")
    return max(dates) if dates else None
