"""Génère la page HTML figée listant les député·e·s ET sénateur·rice·s de
départements donnés (deux onglets, une taxonomie de catégories partagée),
plus un classeur Excel par chambre. Point d'entrée principal des snapshots —
`snapshots/deputes.py` et `snapshots/senateurs.py` restent utilisables
indépendamment (ex: pour ne régénérer qu'un classeur), mais c'est ce module
qui produit la page complète.

Usage :
    python -m votes_parlementaires.snapshots.page --departements 17 79
"""

import argparse
import html
import json
from pathlib import Path

from votes_parlementaires.an.categorize import distinct_textes
from votes_parlementaires.an.categorize import load_categorie_map as an_load_categorie_map
from votes_parlementaires.an.meta import read_build_date
from votes_parlementaires.config import an_snapshots_dir
from votes_parlementaires.senat.categorize import load_categorie_map as senat_load_categorie_map
from votes_parlementaires.senat.data import SenatData
from votes_parlementaires.snapshots.deputes import (
    MOIS_FULL,
    TEMPLATE_PATH,
    GroupRegistry,
    category_color_vars,
    category_tag_rules,
    categories_table_html,
    dept_section_html as an_dept_section_html,
    fmt_date,
    last_scrutin_label,
    load_deputes_data,
    party_color,
    slugify,
    to_roman,
)
from votes_parlementaires.snapshots.senateurs import (
    dept_section_html as senat_dept_section_html,
    load_senateurs_data,
)
from votes_parlementaires.webapp.data import ANData
from votes_parlementaires.an.taxonomy import CATEGORIES


def build_group_registry(legislature: int) -> GroupRegistry:
    """Un seul registre de textes/catégories partagé entre l'AN et le Sénat :
    un même texte de loi débattu dans les deux chambres se retrouve ainsi
    regroupé sous une entrée unique plutôt que dupliqué."""
    an_scrutins = ANData(legislature).scrutins
    senat_scrutins = SenatData().scrutins

    textes = {**distinct_textes(an_scrutins), **distinct_textes(senat_scrutins)}
    categorie_map = {**an_load_categorie_map(legislature), **senat_load_categorie_map()}
    return GroupRegistry(textes, categorie_map)


def generate(
    departements: list[str],
    legislature: int | None = None,
    out: Path | None = None,
    an_xlsx_href: str | None = None,
    senat_xlsx_href: str | None = None,
) -> Path:
    codes = [str(c) for c in departements]

    probe = ANData(legislature)
    legislature = probe.legislature
    groups = build_group_registry(legislature)

    dd = load_deputes_data(departements, legislature, groups=groups)
    sd = load_senateurs_data(departements, groups=groups)

    an_sections, senat_sections = [], []
    used_parties = set()

    for code in codes:
        sub = dd.deps_df[dd.deps_df["num_departement"] == code]
        if not sub.empty:
            an_sections.append(an_dept_section_html(code, sub.iloc[0]["departement"], sub.iloc[0]["region"], sub))
            used_parties.update(sub["groupe_abrege"].fillna("NI"))

        sub_sen = sd.sen_df[sd.sen_df["num_departement"] == code]
        if not sub_sen.empty:
            nom = sub_sen.iloc[0]["departement"]
            region = sub_sen.iloc[0]["region"]
            senat_sections.append(senat_dept_section_html(code, nom, region, sub_sen))
            used_parties.update(sub_sen["groupe_libelle"].fillna("NI"))

    party_color_vars = "\n".join(f"    --party-{slugify(p)}: {party_color(p)};" for p in sorted(used_parties))
    party_pill_rules = "\n".join(
        f"  .pill.party-{slugify(p)} {{ --party: var(--party-{slugify(p)}); }}" for p in sorted(used_parties)
    )

    build_date = read_build_date(legislature)
    if build_date is None:
        snapshot_label = "Date de rafraîchissement inconnue (reconstruire via build.py)"
    else:
        snapshot_label = (
            f"Rafraîchi le <strong>{fmt_date(build_date.isoformat(), MOIS_FULL)}</strong> — "
            f"Assemblée nationale ({to_roman(legislature)}<sup>e</sup> législature) & Sénat"
        )

    dept_names = dd.dept_names or sd.dept_names
    if len(dept_names) > 1:
        joined_names = ", ".join(dept_names[:-1]) + " & " + dept_names[-1]
    else:
        joined_names = dept_names[0]

    title = f"Député·e·s et sénateur·rice·s de {joined_names}"
    eyebrow = "Assemblée nationale &amp; Sénat"
    h1 = joined_names
    subtitle = (
        f"<strong>{len(dd.deps_df)}</strong> circonscriptions à l'Assemblée · "
        f"<strong>{len(sd.sen_df)}</strong> sièges au Sénat"
    )
    dek = (
        f"Cette page présente les votes des député·e·s et sénateur·rice·s en exercice de "
        f"{joined_names} ({', '.join(codes)}), à l'Assemblée nationale comme au Sénat. "
        "Cliquez sur un nom pour consulter l'historique complet de ses votes."
    )

    payload = {"groups": groups.groups, "deputes": {**dd.entries, **sd.entries}}
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
            f'<a class="xlsx-link" href="{html.escape(an_xlsx_href)}" download>⇩ Télécharger les député·e·s en Excel (.xlsx)</a>'
            if an_xlsx_href
            else ""
        ),
        "[[SENATEURS_XLSX_LINK_HTML]]": (
            f'<a class="xlsx-link" href="{html.escape(senat_xlsx_href)}" download>⇩ Télécharger les sénateur·rice·s en Excel (.xlsx)</a>'
            if senat_xlsx_href
            else ""
        ),
        "[[DEPARTMENTS_HTML]]": "\n".join(an_sections),
        "[[SENATEURS_DEPARTMENTS_HTML]]": "\n".join(senat_sections),
        "[[TOTAL_COUNT]]": str(len(dd.deps_df)),
        "[[SENATEURS_TOTAL_COUNT]]": str(len(sd.sen_df)),
        "[[LAST_SCRUTIN_AN]]": last_scrutin_label(dd.data.scrutins),
        "[[LAST_SCRUTIN_SENAT]]": last_scrutin_label(sd.data.scrutins),
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
        out = an_snapshots_dir(legislature) / f"elus-{'-'.join(codes)}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_out, encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Génère la page HTML figée (député·e·s + sénateur·rice·s) et leurs classeurs Excel."
    )
    parser.add_argument("--departements", nargs="+", default=["17", "79"], help="Numéros de département (ex: 17 79).")
    parser.add_argument("--legislature", type=int, default=None, help="Forcer une législature AN (par défaut: la plus récente déjà construite).")
    parser.add_argument("--out", type=Path, default=None, help="Chemin de sortie HTML (par défaut: data/snapshots/an/<législature>/elus-<deps>.html).")
    parser.add_argument("--no-xlsx", action="store_true", help="Ne génère pas les classeurs Excel, ni les liens de téléchargement sur la page.")
    args = parser.parse_args()

    an_xlsx_href = senat_xlsx_href = None
    if not args.no_xlsx:
        from votes_parlementaires.snapshots.deputes_xlsx import generate as generate_an_xlsx
        from votes_parlementaires.snapshots.senateurs_xlsx import generate as generate_senat_xlsx

        an_xlsx_out = args.out.with_name(args.out.stem + "-deputes.xlsx") if args.out is not None else None
        an_xlsx = generate_an_xlsx(args.departements, legislature=args.legislature, out=an_xlsx_out)
        an_xlsx_href = an_xlsx.name
        print(f"Classeur Excel (député·e·s) généré : {an_xlsx}")

        senat_xlsx_out = args.out.with_name(args.out.stem + "-senateurs.xlsx") if args.out is not None else None
        senat_xlsx = generate_senat_xlsx(args.departements, out=senat_xlsx_out)
        senat_xlsx_href = senat_xlsx.name
        print(f"Classeur Excel (sénateur·rice·s) généré : {senat_xlsx}")

    out = generate(
        args.departements,
        legislature=args.legislature,
        out=args.out,
        an_xlsx_href=an_xlsx_href,
        senat_xlsx_href=senat_xlsx_href,
    )
    print(f"Page générée : {out}")


if __name__ == "__main__":
    main()
