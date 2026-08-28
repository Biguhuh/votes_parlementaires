import re

from bs4 import BeautifulSoup

# Les 4 intitulés utilisés par le Sénat pour les 4 blocs de la section
# "Analyse détaillée" de chaque page de scrutin, mappés vers les mêmes codes
# de position que ceux utilisés côté Assemblée nationale (votes_parlementaires.an.parse).
POSITION_LABELS = {
    "ont voté pour": "pour",
    "ont voté contre": "contre",
    "abstentions": "abstention",
    "n'ont pas pris part au vote": "nonVotant",
}

# Ex: "bazin_arnaud19667j" -> matricule "19667J" (même identifiant que la
# colonne "Matricule" de l'export sénateurs, voir senat/parse.py).
MATRICULE_RE = re.compile(r"/senateur/([a-z_]+(\d{5}[a-z]))\.html$", re.IGNORECASE)

MOIS = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}
DATE_RE = re.compile(r"séance du (\d{1,2})(?:er)? (\w+) (\d{4})", re.IGNORECASE)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_date_seance(title: str) -> str | None:
    m = DATE_RE.search(title)
    if not m:
        return None
    jour, mois_nom, annee = m.groups()
    mois = MOIS.get(mois_nom.lower())
    if mois is None:
        return None
    return f"{annee}-{mois:02d}-{int(jour):02d}"


def parse_scrutin_page(html_text: str, annee: int, numero: int) -> dict:
    """Métadonnées + décompte + votes individuels d'une page de scrutin public
    du Sénat (senat.fr/scrutin-public/<annee>/scr<annee>-<numero>.html)."""
    soup = BeautifulSoup(html_text, "html.parser")

    title = _clean(soup.select_one("h1.page-title").get_text(" ", strip=True))
    lead = soup.select_one("p.page-lead")
    badge = soup.select_one(".badge.rounded-pill")

    counts = {}
    for li in soup.select("ul.list-unstyled.row li"):
        strong = li.find("strong")
        if not strong:
            continue
        label = _clean(li.get_text(" ", strip=True).replace(strong.get_text(strip=True), ""))
        counts[label] = int(strong.get_text(strip=True))
    for li in soup.select("ul.list-inline.text-center li"):
        m = re.match(r"(.+?)\s*:\s*(\d+)", _clean(li.get_text(" ", strip=True)))
        if m:
            counts[m.group(1).strip().lower()] = int(m.group(2))

    scrutin = {
        "scrutin_ref": f"senat-{annee}-{numero}",
        "annee_session": annee,
        "numero": numero,
        "date_scrutin": _parse_date_seance(title),
        "titre": _clean(lead.get_text(" ", strip=True)) if lead else None,
        "sort_libelle": badge.get_text(strip=True) if badge else None,
        "nombre_votants": counts.get("votants"),
        "suffrages_exprimes": counts.get("suffrages exprimés"),
        "decompte_pour": counts.get("pour"),
        "decompte_contre": counts.get("contre"),
        "decompte_abstentions": counts.get("abstention"),
        "decompte_non_votants": counts.get("n'ont pas pris part au vote"),
    }

    votes = []
    slugs = {}
    detail_section = None
    for h2 in soup.find_all("h2"):
        if "Analyse détaillée" in h2.get_text():
            detail_section = h2.find_parent("section")
            break

    if detail_section is not None:
        for item in detail_section.select(".accordion-item"):
            header_btn = item.select_one(".accordion-header button")
            if not header_btn:
                continue
            label = _clean(header_btn.get_text(" ", strip=True)).lower()
            position = POSITION_LABELS.get(label)
            if position is None:
                continue
            for a in item.select("a.senator_lnk"):
                href = a.get("href") or ""
                m = MATRICULE_RE.search(href)
                if not m:
                    continue
                slug, matricule = m.group(1), m.group(2).upper()
                votes.append(
                    {
                        "scrutin_ref": scrutin["scrutin_ref"],
                        "senateur_ref": matricule,
                        "position": position,
                    }
                )
                slugs[matricule] = slug

    return {"scrutin": scrutin, "votes": votes, "slugs": slugs}
