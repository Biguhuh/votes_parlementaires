"""Génère les données (entrées HTML + JSON de votes) des sénateur·rice·s de
départements donnés, avec leur historique complet de scrutins depuis le
début de leur mandat en cours. Miroir de `snapshots/deputes.py` côté Sénat —
mêmes structures de données, réutilisées telles quelles par le gabarit HTML
et par le classeur Excel.

Contrairement aux député·e·s (dont la participation est mesurée depuis leur
premier vote enregistré, faute de date de mandat dans les données AN), les
sénateur·rice·s ont une vraie date de début de mandat (`mandats.csv`, voir
senat/build_mandats.py) : la participation n'est comptée qu'à partir de
cette date.
"""

import html

from votes_parlementaires.senat.data import POSITIONS, SenatData
from votes_parlementaires.snapshots.deputes import (
    MOIS_ABBR,
    MOIS_FULL,
    GroupRegistry,
    fmt_date,
    party_color,
    slugify,
)


def build_senateur_entry(data: SenatData, senateur_ref: str, groups: GroupRegistry, depuis_iso: str | None) -> dict:
    votes_df = data.senateur_votes(senateur_ref)
    if depuis_iso:
        votes_df = votes_df[votes_df["date_scrutin"] >= depuis_iso]

    stats = {p: int((votes_df["position"] == p).sum()) for p in POSITIONS}

    dates = votes_df["date_scrutin"].dropna()
    if dates.empty:
        possible, recorded, since, min_iso, max_iso = 0, 0, None, None, None
    else:
        dmin = depuis_iso or dates.min()
        dmax = dates.max()
        in_range = data.scrutins[(data.scrutins["date_scrutin"] >= dmin) & (data.scrutins["date_scrutin"] <= dmax)]
        possible = len(in_range)
        recorded = len(votes_df)
        since = fmt_date(dmin, MOIS_FULL)
        min_iso, max_iso = dmin, dmax

    votes = []
    for row in votes_df.itertuples():
        gi, action = groups.get(row.titre)
        votes.append(
            {
                "iso": row.date_scrutin or "",
                "d": fmt_date(row.date_scrutin, MOIS_ABBR),
                "t": row.titre or "",
                "a": action,
                "gi": gi,
                "r": row.sort_libelle or "",
                "p": row.position,
                "g": False,
            }
        )

    return {
        "stats": stats,
        "possible": possible,
        "recorded": recorded,
        "since": since,
        "minDate": min_iso,
        "maxDate": max_iso,
        "votes": votes,
    }


def senateur_button_html(row) -> str:
    nom_complet = html.escape(row.nom_complet)
    civ = html.escape(row.civ or "")
    groupe_abrege = row.groupe_libelle or "NI"
    slug = slugify(groupe_abrege)

    return f"""        <li>
          <button class="who" type="button" data-ref="{row.senateur_ref}" data-name="{nom_complet}" data-civ="{civ}" data-party-full="{html.escape(groupe_abrege)}" data-party-label="{html.escape(groupe_abrege)}">
            <div class="name"><span class="civ">{civ}</span>{nom_complet} <span class="arrow">→</span></div>
            <span class="pill party-{slug}"><span class="swatch"></span><span class="label">{html.escape(groupe_abrege)}</span></span>
            <div class="stats-mini" data-stats-for="{row.senateur_ref}"></div>
          </button>
        </li>"""


def dept_section_html(code: str, nom: str, region, senateurs) -> str:
    items = "\n".join(senateur_button_html(row) for row in senateurs.itertuples())
    region_html = f'<span class="region">{html.escape(region)}</span>' if isinstance(region, str) else ""
    return f"""    <section class="dept">
      <div class="dept-head">
        <div>
          <h2>{html.escape(nom)}</h2>
          {region_html}
        </div>
        <span class="num">{code}</span>
      </div>
      <ol class="circ-list flat">
{items}
      </ol>
    </section>"""


class SenateursData:
    def __init__(self, data: SenatData, sen_df, groups: GroupRegistry, entries: dict, dept_names: list[str]):
        self.data = data
        self.sen_df = sen_df
        self.groups = groups
        self.entries = entries
        self.dept_names = dept_names


def load_senateurs_data(departements: list[str], groups: GroupRegistry) -> SenateursData:
    data = SenatData()

    codes = [str(c) for c in departements]
    sen_df = data.senateurs_actifs[data.senateurs_actifs["num_departement"].isin(codes)].copy()
    sen_df = sen_df.sort_values(["num_departement", "nom"])

    if sen_df.empty:
        raise SystemExit(f"Aucun·e sénateur·rice trouvé·e pour les départements {codes}.")

    entries = {}
    dept_names = []
    for code in codes:
        sub = sen_df[sen_df["num_departement"] == code]
        if sub.empty:
            continue
        dept_names.append(sub.iloc[0]["departement"])
        for row in sub.itertuples():
            entries[row.senateur_ref] = build_senateur_entry(data, row.senateur_ref, groups, row.depuis)

    return SenateursData(data, sen_df, groups, entries, dept_names)
