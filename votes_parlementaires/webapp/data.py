import unicodedata

import pandas as pd

from votes_parlementaires.an.legislature import detect_current_legislature
from votes_parlementaires.config import an_processed_dir

POSITIONS = ["pour", "contre", "abstention", "nonVotant"]

# Colonnes identifiantes : forcées en texte pour éviter les artefacts de
# pandas qui promeut en float64 dès qu'une colonne d'entiers contient des NaN
# (ex: "5" devenu "5.0").
ID_DTYPES = {
    "scrutin_uid": "string",
    "numero": "string",
    "acteur_ref": "string",
    "mandat_ref": "string",
    "groupe_organe_ref": "string",
    "organe_ref": "string",
    "groupe_actuel_ref": "string",
    "num_departement": "string",
    "num_circonscription": "string",
}


def normalize(text) -> str:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    text = str(text)
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    ).lower()


def _clean_records(df: pd.DataFrame) -> list[dict]:
    """Convertit un DataFrame en liste de dicts JSON-sérialisables (NaN -> None)."""
    return df.astype(object).where(pd.notnull(df), None).to_dict("records")


class ANData:
    def __init__(self, legislature: int | None = None):
        self.legislature = legislature or detect_current_legislature()
        d = an_processed_dir(self.legislature)

        self.scrutins = pd.read_csv(d / "scrutins.csv", dtype=ID_DTYPES)
        self.votes = pd.read_csv(d / "votes.csv", dtype=ID_DTYPES)
        self.acteurs = pd.read_csv(d / "acteurs.csv", dtype=ID_DTYPES)
        self.organes = pd.read_csv(d / "organes.csv", dtype=ID_DTYPES)

        self._prepare()

    def _prepare(self) -> None:
        self.acteurs["nom_complet"] = (
            self.acteurs["prenom"].fillna("") + " " + self.acteurs["nom"].fillna("")
        ).str.strip()

        groupes = self.organes.set_index("organe_ref")[["libelle", "libelle_abrege"]].rename(
            columns={"libelle": "groupe_libelle", "libelle_abrege": "groupe_abrege"}
        )
        self.acteurs = self.acteurs.merge(
            groupes, left_on="groupe_actuel_ref", right_index=True, how="left"
        )

        self.acteurs["_search"] = (
            self.acteurs["nom_complet"].map(normalize)
            + " "
            + self.acteurs["departement"].map(normalize)
            + " "
            + self.acteurs["num_circonscription"].fillna("").astype(str)
            + " "
            + self.acteurs["num_departement"].fillna("").astype(str)
        )

        # Seuls les acteurs avec un siège actif (dateFin nulle sur leur mandat
        # ASSEMBLEE) ont un département/circonscription : ce sont les députés
        # actuellement en exercice.
        self.deputes_actifs = self.acteurs[self.acteurs["departement"].notna()].copy()
        self.deputes_actifs = self.deputes_actifs.sort_values("nom")

        self.vote_counts = (
            self.votes.groupby(["acteur_ref", "position"]).size().unstack(fill_value=0)
        )
        for col in POSITIONS:
            if col not in self.vote_counts.columns:
                self.vote_counts[col] = 0

        self.scrutins = self.scrutins.sort_values("date_scrutin", ascending=False)
        self.scrutins["_search"] = self.scrutins["titre"].map(normalize)

        self.scrutins_by_uid = self.scrutins.set_index("scrutin_uid", drop=False)
        self.organes_by_ref = self.organes.set_index("organe_ref", drop=False)

    # -- députés --------------------------------------------------------

    def stats_for(self, acteur_ref: str) -> dict:
        if acteur_ref in self.vote_counts.index:
            row = self.vote_counts.loc[acteur_ref]
            return {p: int(row[p]) for p in POSITIONS}
        return {p: 0 for p in POSITIONS}

    def search_deputes(self, q: str) -> pd.DataFrame:
        df = self.deputes_actifs
        if q:
            nq = normalize(q)
            df = df[df["_search"].str.contains(nq, regex=False)]
        return df

    def deputes_to_dicts(self, df: pd.DataFrame) -> list[dict]:
        records = _clean_records(
            df[
                [
                    "acteur_ref",
                    "civ",
                    "nom_complet",
                    "groupe_actuel_ref",
                    "groupe_libelle",
                    "groupe_abrege",
                    "region",
                    "departement",
                    "num_departement",
                    "num_circonscription",
                ]
            ]
        )
        for r in records:
            r["stats"] = self.stats_for(r["acteur_ref"])
        return records

    def depute(self, acteur_ref: str) -> dict | None:
        matches = self.acteurs[self.acteurs["acteur_ref"] == acteur_ref]
        if matches.empty:
            return None
        record = self.deputes_to_dicts(matches)[0]
        return record

    def depute_votes(self, acteur_ref: str, q: str = "") -> pd.DataFrame:
        df = self.votes[self.votes["acteur_ref"] == acteur_ref]
        df = df.merge(
            self.scrutins[["scrutin_uid", "date_scrutin", "titre", "sort_libelle", "_search"]],
            on="scrutin_uid",
            how="left",
        )
        if q:
            nq = normalize(q)
            df = df[df["_search"].str.contains(nq, regex=False)]
        return df.sort_values("date_scrutin", ascending=False)[
            ["scrutin_uid", "date_scrutin", "titre", "sort_libelle", "position", "par_delegation"]
        ]

    # -- groupes ----------------------------------------------------------

    def groupes(self) -> list[dict]:
        refs = self.deputes_actifs["groupe_actuel_ref"].dropna().unique()
        by_groupe = self.votes.groupby(["groupe_organe_ref", "position"]).size().unstack(fill_value=0)

        results = []
        for ref in refs:
            organe = self.organes_by_ref.loc[ref] if ref in self.organes_by_ref.index else None
            effectif = int((self.deputes_actifs["groupe_actuel_ref"] == ref).sum())
            stats = {p: int(by_groupe.loc[ref, p]) for p in POSITIONS} if ref in by_groupe.index else {
                p: 0 for p in POSITIONS
            }
            results.append(
                {
                    "organe_ref": ref,
                    "libelle": None if organe is None else organe["libelle"],
                    "libelle_abrege": None if organe is None else organe["libelle_abrege"],
                    "effectif": effectif,
                    "stats": stats,
                }
            )
        return sorted(results, key=lambda g: g["effectif"], reverse=True)

    def groupe(self, organe_ref: str) -> dict | None:
        if organe_ref not in self.organes_by_ref.index:
            return None
        organe = self.organes_by_ref.loc[organe_ref]
        membres = self.deputes_actifs[self.deputes_actifs["groupe_actuel_ref"] == organe_ref]
        return {
            "organe_ref": organe_ref,
            "libelle": organe["libelle"],
            "libelle_abrege": organe["libelle_abrege"],
            "membres": self.deputes_to_dicts(membres),
        }

    # -- scrutins -----------------------------------------------------------

    def search_scrutins(self, q: str) -> pd.DataFrame:
        df = self.scrutins
        if q:
            nq = normalize(q)
            df = df[df["_search"].str.contains(nq, regex=False)]
        return df

    def scrutin(self, scrutin_uid: str) -> dict | None:
        if scrutin_uid not in self.scrutins_by_uid.index:
            return None
        meta = _clean_records(self.scrutins_by_uid.loc[[scrutin_uid]])[0]
        del meta["_search"]

        votes = self.votes[self.votes["scrutin_uid"] == scrutin_uid].merge(
            self.acteurs[["acteur_ref", "nom_complet"]], on="acteur_ref", how="left"
        )
        by_groupe = votes.groupby(["groupe_organe_ref", "position"]).size().unstack(fill_value=0)
        par_groupe = []
        for ref, row in by_groupe.iterrows():
            organe = self.organes_by_ref.loc[ref] if ref in self.organes_by_ref.index else None
            par_groupe.append(
                {
                    "organe_ref": ref,
                    "libelle_abrege": None if organe is None else organe["libelle_abrege"],
                    **{p: int(row.get(p, 0)) for p in POSITIONS},
                }
            )
        par_groupe.sort(key=lambda g: sum(g[p] for p in POSITIONS), reverse=True)

        votants = _clean_records(
            votes.merge(
                self.organes[["organe_ref", "libelle_abrege"]].rename(
                    columns={"libelle_abrege": "groupe_abrege"}
                ),
                left_on="groupe_organe_ref",
                right_on="organe_ref",
                how="left",
            )[["acteur_ref", "nom_complet", "groupe_abrege", "position"]]
        )

        meta["par_groupe"] = par_groupe
        meta["votants"] = votants
        return meta
