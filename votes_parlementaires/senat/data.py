import pandas as pd

from votes_parlementaires.config import senat_processed_dir

POSITIONS = ["pour", "contre", "abstention", "nonVotant"]


class SenatData:
    """Équivalent, côté Sénat, de `votes_parlementaires.webapp.data.ANData` :
    charge les CSV construits par `senat.build` / `senat.build_votes` /
    `senat.build_mandats` et expose les mêmes primitives (stats, votes d'un
    élu) qu'utilise le générateur de page figée."""

    def __init__(self):
        d = senat_processed_dir()
        self.senateurs = pd.read_csv(d / "senateurs.csv", dtype={"num_departement": "string"})
        self.scrutins = pd.read_csv(d / "scrutins.csv")
        self.votes = pd.read_csv(d / "votes.csv")

        mandats_path = d / "mandats.csv"
        self.mandats = (
            pd.read_csv(mandats_path)
            if mandats_path.exists()
            else pd.DataFrame(columns=["senateur_ref", "depuis"])
        )

        self._prepare()

    def _prepare(self) -> None:
        self.senateurs["nom_complet"] = (
            self.senateurs["prenom"].fillna("") + " " + self.senateurs["nom"].fillna("")
        ).str.strip()
        self.senateurs = self.senateurs.merge(self.mandats, on="senateur_ref", how="left")

        self.scrutins = self.scrutins.sort_values("date_scrutin", ascending=False)

        self.vote_counts = self.votes.groupby(["senateur_ref", "position"]).size().unstack(fill_value=0)
        for col in POSITIONS:
            if col not in self.vote_counts.columns:
                self.vote_counts[col] = 0

        # Tou·te·s les sénateur·rice·s de l'export sont déjà "actif·ve·s"
        # (etat == ACTIF, filtré dès senat/parse.py) ; on ne garde ici que
        # celles et ceux rattaché·e·s à un département identifiable.
        self.senateurs_actifs = self.senateurs[self.senateurs["departement"].notna()].copy()
        self.senateurs_actifs = self.senateurs_actifs.sort_values("nom")

    def stats_for(self, senateur_ref: str) -> dict:
        if senateur_ref in self.vote_counts.index:
            row = self.vote_counts.loc[senateur_ref]
            return {p: int(row[p]) for p in POSITIONS}
        return {p: 0 for p in POSITIONS}

    def senateur_votes(self, senateur_ref: str) -> pd.DataFrame:
        df = self.votes[self.votes["senateur_ref"] == senateur_ref]
        df = df.merge(
            self.scrutins[["scrutin_ref", "date_scrutin", "titre", "sort_libelle"]],
            on="scrutin_ref",
            how="left",
        )
        return df.sort_values("date_scrutin", ascending=False)[
            ["scrutin_ref", "date_scrutin", "titre", "sort_libelle", "position"]
        ]
