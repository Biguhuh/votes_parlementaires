"""Génère une page HTML statique (données figées) listant les député·e·s de
départements donnés, avec leurs statistiques de vote et l'historique complet
de leurs scrutins. Pensé pour être relancé plus tard, une fois de nouvelles
données téléchargées (`python -m votes_parlementaires.an.build`), afin de
produire une version à jour de la même page.

Usage :
    python -m votes_parlementaires.snapshots.deputes --departements 17 79
"""

import argparse
import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path

from votes_parlementaires.an.categorize import (
    FALLBACK_CATEGORY,
    distinct_textes,
    load_categorie_map,
    normalize_key,
    split_titre,
)
from votes_parlementaires.an.meta import read_build_date
from votes_parlementaires.an.taxonomy import CATEGORIES
from votes_parlementaires.config import an_snapshots_dir
from votes_parlementaires.webapp.data import ANData

TEMPLATE_PATH = Path(__file__).parent / "template.html"

MOIS_ABBR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MOIS_FULL = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

RESULT_LABELS = {
    "l'Assemblée nationale a adopté": "Adopté",
    "L'Assemblée nationale a adopté": "Adopté",
    "l'Assemblée nationale n'a pas adopté": "Rejeté",
    "L'Assemblée nationale n'a pas adopté": "Rejeté",
}

# Couleurs connues pour les groupes politiques de l'AN (mandature en cours).
# Un groupe absent de cette table (nouvelle mandature, dissolution...) reçoit
# une couleur choisie automatiquement dans EXTRA_PALETTE, de façon stable.
KNOWN_PARTY_COLORS = {
    "rn": "#6b6558",
    "dr": "#a15a34",
    "gdr": "#9c3f4a",
    "dem": "#c98a2a",
    "soc": "#c1547a",
    "liot": "#7d8a3f",
    "lfi-nfp": "#8a3f8a",
    "udr": "#4f5f99",
    "epr": "#3565a8",
    "ecos": "#3f8a56",
    "hor": "#1f8f88",
    "ni": "#7c8894",
}
EXTRA_PALETTE = ["#a15a34", "#3f8a99", "#8a5f3f", "#5f7d99", "#997d3f", "#7d3f99"]

ROMAN_NUMERALS = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def to_roman(n: int) -> str:
    result = ""
    for value, symbol in ROMAN_NUMERALS:
        while n >= value:
            result += symbol
            n -= value
    return result


def fmt_date(iso_date: str, months: list[str]) -> str:
    try:
        y, m, d = iso_date.split("-")
        return f"{int(d)} {months[int(m) - 1]} {y}"
    except (ValueError, IndexError, AttributeError):
        return iso_date or ""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def last_scrutin_label(scrutins) -> str:
    """Date du scrutin le plus récent d'un DataFrame de scrutins, distincte
    de la date de rafraîchissement des données : la source (data.gouv,
    senat.fr) peut avoir du retard sur les scrutins tenus les jours
    précédents."""
    dates = scrutins["date_scrutin"].dropna()
    if dates.empty:
        return "inconnu"
    return fmt_date(dates.max(), MOIS_FULL)


def party_color(groupe_abrege: str | None) -> str:
    if not groupe_abrege:
        return KNOWN_PARTY_COLORS["ni"]
    slug = slugify(groupe_abrege)
    if slug in KNOWN_PARTY_COLORS:
        return KNOWN_PARTY_COLORS[slug]
    idx = int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(EXTRA_PALETTE)
    return EXTRA_PALETTE[idx]


class GroupRegistry:
    """Regroupe les scrutins par texte législatif sous-jacent : un même texte
    (ex: le PLF 2026) donne lieu à des centaines de scrutins (un par
    amendement/article/lecture), tous rattachés au même groupe et à la même
    catégorie plutôt que d'être classés individuellement."""

    FALLBACK_KEY = "__autre__"

    def __init__(self, textes_by_key: dict[str, str], categorie_map: dict[str, str]):
        self.textes_by_key = textes_by_key
        self.categorie_map = categorie_map
        self.index: dict[str, int] = {}
        self.groups: list[list[str]] = []

    def get(self, titre: str) -> tuple[int, str | None]:
        action, texte_raw = split_titre(titre)
        if texte_raw is None:
            key, texte_display, cat = self.FALLBACK_KEY, "Autres scrutins", FALLBACK_CATEGORY
        else:
            key = normalize_key(texte_raw)
            texte_display = self.textes_by_key.get(key, texte_raw)
            cat = self.categorie_map.get(key, FALLBACK_CATEGORY)
        if key not in self.index:
            self.index[key] = len(self.groups)
            self.groups.append([texte_display, cat])
        return self.index[key], action


def build_depute_entry(data: ANData, acteur_ref: str, groups: GroupRegistry) -> dict:
    votes_df = data.depute_votes(acteur_ref)
    stats = data.stats_for(acteur_ref)

    dates = votes_df["date_scrutin"].dropna()
    if dates.empty:
        possible, recorded, since, min_iso, max_iso = 0, 0, None, None, None
    else:
        dmin, dmax = dates.min(), dates.max()
        in_range = data.scrutins[
            (data.scrutins["date_scrutin"] >= dmin) & (data.scrutins["date_scrutin"] <= dmax)
        ]
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
                "r": RESULT_LABELS.get(row.sort_libelle, row.sort_libelle or ""),
                "p": row.position,
                "g": bool(row.par_delegation) and str(row.par_delegation).lower() == "true",
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


def depute_button_html(row, entry_key: str) -> str:
    nom_complet = html.escape(row.nom_complet)
    civ = html.escape(row.civ or "")
    groupe_abrege = row.groupe_abrege or "NI"
    groupe_libelle = row.groupe_libelle or "Non inscrit"
    slug = slugify(groupe_abrege)

    return f"""        <li>
          <span class="circ-num">{row.num_circonscription}</span>
          <button class="who" type="button" data-ref="{row.acteur_ref}" data-name="{nom_complet}" data-civ="{civ}" data-party-full="{html.escape(groupe_libelle)}" data-party-label="{html.escape(groupe_abrege)}">
            <div class="name"><span class="civ">{civ}</span>{nom_complet} <span class="arrow">→</span></div>
            <span class="pill party-{slug}"><span class="swatch"></span><span class="label">{html.escape(groupe_abrege)}</span><span class="full">{html.escape(groupe_libelle)}</span></span>
            <div class="stats-mini" data-stats-for="{row.acteur_ref}"></div>
          </button>
        </li>"""


def dept_section_html(code: str, nom: str, region: str, deputes) -> str:
    items = "\n".join(depute_button_html(row, row.acteur_ref) for row in deputes.itertuples())
    return f"""    <section class="dept">
      <div class="dept-head">
        <div>
          <h2>{html.escape(nom)}</h2>
          <span class="region">{html.escape(region)}</span>
        </div>
        <span class="num">{code}</span>
      </div>
      <ol class="circ-list">
{items}
      </ol>
    </section>"""


def categories_table_html() -> str:
    return "\n".join(
        f'          <tr><td class="cat-label"><span class="cat-tag cat-{c["id"]}"><span class="swatch"></span>{html.escape(c["label"])}</span></td>'
        f'<td class="cat-desc">{html.escape(c["description"])}</td>'
        f'<td class="cat-id">{html.escape(c["id"])}</td></tr>'
        for c in CATEGORIES
    )


def category_color_vars() -> str:
    return "\n".join(f"    --cat-{c['id']}: {c['color']};" for c in CATEGORIES)


def category_tag_rules() -> str:
    return "\n".join(f"  .cat-tag.cat-{c['id']} {{ --cat: var(--cat-{c['id']}); }}" for c in CATEGORIES)


class DeputesData:
    """Données déjà collectées pour un ensemble de départements : la table
    des député·e·s, le registre de groupes (textes législatifs + catégorie),
    et l'entrée (stats + votes) de chacun·e. Partagé entre les générateurs de
    sortie (HTML, Excel...) pour ne pas dupliquer la collecte."""

    def __init__(self, data: ANData, deps_df, groups: GroupRegistry, entries: dict, dept_names: list[str]):
        self.data = data
        self.deps_df = deps_df
        self.groups = groups
        self.entries = entries
        self.dept_names = dept_names
        self.legislature = data.legislature


def load_deputes_data(
    departements: list[str], legislature: int | None = None, groups: GroupRegistry | None = None
) -> DeputesData:
    data = ANData(legislature)
    legislature = data.legislature

    codes = [str(c) for c in departements]
    deps_df = data.deputes_actifs[data.deputes_actifs["num_departement"].isin(codes)].copy()
    deps_df["num_circonscription"] = deps_df["num_circonscription"].astype(int)
    deps_df = deps_df.sort_values(["num_departement", "num_circonscription"])

    if deps_df.empty:
        raise SystemExit(f"Aucun·e député·e trouvé·e pour les départements {codes}.")

    if groups is None:
        groups = GroupRegistry(distinct_textes(data.scrutins), load_categorie_map(legislature))

    entries = {}
    dept_names = []
    for code in codes:
        sub = deps_df[deps_df["num_departement"] == code]
        if sub.empty:
            continue
        dept_names.append(sub.iloc[0]["departement"])
        for row in sub.itertuples():
            entries[row.acteur_ref] = build_depute_entry(data, row.acteur_ref, groups)

    return DeputesData(data, deps_df, groups, entries, dept_names)


def generate(
    departements: list[str],
    legislature: int | None = None,
    out: Path | None = None,
    xlsx_href: str | None = None,
) -> Path:
    dd = load_deputes_data(departements, legislature)
    data, deps_df, groups, votes_data, dept_names = dd.data, dd.deps_df, dd.groups, dd.entries, dd.dept_names
    legislature = dd.legislature
    codes = [str(c) for c in departements]

    sections = []
    used_parties = set()

    for code in codes:
        sub = deps_df[deps_df["num_departement"] == code]
        if sub.empty:
            continue
        nom = sub.iloc[0]["departement"]
        region = sub.iloc[0]["region"]
        sections.append(dept_section_html(code, nom, region, sub))
        for row in sub.itertuples():
            used_parties.add(row.groupe_abrege or "NI")

    party_color_vars = "\n".join(
        f"    --party-{slugify(p)}: {party_color(p)};" for p in sorted(used_parties)
    )
    party_pill_rules = "\n".join(
        f"  .pill.party-{slugify(p)} {{ --party: var(--party-{slugify(p)}); }}" for p in sorted(used_parties)
    )

    build_date = read_build_date(legislature)
    if build_date is None:
        snapshot_label = "Date de rafraîchissement inconnue (reconstruire via build.py) — source data.assemblee-nationale.fr"
    else:
        snapshot_label = f"Rafraîchi le <strong>{fmt_date(build_date.isoformat(), MOIS_FULL)}</strong> — source data.assemblee-nationale.fr"

    if len(dept_names) > 1:
        joined_names = ", ".join(dept_names[:-1]) + " & " + dept_names[-1]
    else:
        joined_names = dept_names[0]

    title = f"Députés de {joined_names}"
    eyebrow = f"Assemblée nationale · {to_roman(legislature)}<sup>e</sup> législature"
    h1 = joined_names
    subtitle = f"<strong>{len(deps_df)}</strong> circonscriptions sur {len(dept_names)} départements"
    dek = (
        f"Cette page présente les votes des député·e·s en exercice de {joined_names} "
        f"({', '.join(codes)}), classés par circonscription. "
        "Cliquez sur un nom pour consulter l'historique complet de ses votes."
    )

    payload = {"groups": groups.groups, "deputes": votes_data}
    votes_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    html_out = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "[[TITLE]]": title,
        "[[EYEBROW]]": eyebrow,
        "[[H1]]": h1,
        "[[SUBTITLE]]": subtitle,
        "[[DEK]]": dek,
        "[[SNAPSHOT_LABEL]]": snapshot_label,
        "[[XLSX_LINK_HTML]]": (
            f'<a class="xlsx-link" href="{html.escape(xlsx_href)}" download>⇩ Télécharger en Excel (.xlsx)</a>'
            if xlsx_href
            else ""
        ),
        "[[DEPARTMENTS_HTML]]": "\n".join(sections),
        "[[TOTAL_COUNT]]": str(len(deps_df)),
        "[[LAST_SCRUTIN_AN]]": last_scrutin_label(data.scrutins),
        # Généré seul (hors snapshots.page), ce module ne produit pas
        # l'onglet Sénateur·rice·s : ces placeholders restent vides.
        "[[SENATEURS_XLSX_LINK_HTML]]": "",
        "[[SENATEURS_DEPARTMENTS_HTML]]": "",
        "[[SENATEURS_TOTAL_COUNT]]": "0",
        "[[LAST_SCRUTIN_SENAT]]": "n/a",
        "[[PARTY_COLOR_VARS]]": party_color_vars,
        "[[PARTY_PILL_RULES]]": party_pill_rules,
        "[[VOTES_JSON]]": votes_json,
        "[[CATEGORIES_HTML]]": categories_table_html(),
        "[[CATEGORY_COLOR_VARS]]": category_color_vars(),
        "[[CATEGORY_TAG_RULES]]": category_tag_rules(),
        "[[CATEGORY_LABELS_JSON]]": json.dumps(
            {c["id"]: c["label"] for c in CATEGORIES}, ensure_ascii=False
        ).replace("</", "<\\/"),
    }
    for token, value in replacements.items():
        html_out = html_out.replace(token, value)

    if out is None:
        out = an_snapshots_dir(legislature) / f"deputes-{'-'.join(codes)}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_out, encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère une page HTML figée listant les député·e·s de départements donnés.")
    parser.add_argument("--departements", nargs="+", default=["17", "79"], help="Numéros de département (ex: 17 79).")
    parser.add_argument("--legislature", type=int, default=None, help="Forcer une législature (par défaut: la plus récente déjà construite).")
    parser.add_argument("--out", type=Path, default=None, help="Chemin de sortie (par défaut: data/snapshots/an/<législature>/deputes-<deps>.html).")
    parser.add_argument("--no-xlsx", action="store_true", help="Ne génère pas le classeur Excel associé, ni le lien de téléchargement sur la page.")
    args = parser.parse_args()

    xlsx_href = None
    if not args.no_xlsx:
        from votes_parlementaires.snapshots.deputes_xlsx import generate as generate_xlsx

        xlsx_out_arg = args.out.with_suffix(".xlsx") if args.out is not None else None
        xlsx_out = generate_xlsx(args.departements, legislature=args.legislature, out=xlsx_out_arg)
        xlsx_href = xlsx_out.name
        print(f"Classeur Excel généré : {xlsx_out}")

    out = generate(args.departements, legislature=args.legislature, out=args.out, xlsx_href=xlsx_href)
    print(f"Page générée : {out}")


if __name__ == "__main__":
    main()
