import json
import zipfile
from pathlib import Path
from typing import Iterator

import pandas as pd

POSITIONS = {
    "pours": "pour",
    "contres": "contre",
    "abstentions": "abstention",
    "nonVotants": "nonVotant",
}


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _votants(category: dict | None) -> list[dict]:
    if not category:
        return []
    return _as_list(category.get("votant"))


def iter_scrutins(zip_path: Path) -> Iterator[dict]:
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            with zf.open(name) as f:
                yield json.load(f)["scrutin"]


def scrutin_record(scrutin: dict) -> dict:
    synthese = scrutin.get("syntheseVote") or {}
    decompte = synthese.get("decompte") or {}
    return {
        "scrutin_uid": scrutin["uid"],
        "numero": scrutin["numero"],
        "legislature": scrutin["legislature"],
        "organe_voteur_ref": scrutin["organeRef"],
        "date_scrutin": scrutin["dateScrutin"],
        "type_vote_code": (scrutin.get("typeVote") or {}).get("codeTypeVote"),
        "type_vote_libelle": (scrutin.get("typeVote") or {}).get("libelleTypeVote"),
        "sort_code": (scrutin.get("sort") or {}).get("code"),
        "sort_libelle": (scrutin.get("sort") or {}).get("libelle"),
        "titre": scrutin.get("titre"),
        "demandeur": (scrutin.get("demandeur") or {}).get("texte"),
        "nombre_votants": synthese.get("nombreVotants"),
        "suffrages_exprimes": synthese.get("suffragesExprimes"),
        "suffrages_requis": synthese.get("nbrSuffragesRequis"),
        "decompte_pour": decompte.get("pour"),
        "decompte_contre": decompte.get("contre"),
        "decompte_abstentions": decompte.get("abstentions"),
        "decompte_non_votants": decompte.get("nonVotants"),
    }


def vote_records(scrutin: dict) -> Iterator[dict]:
    ventilation = scrutin.get("ventilationVotes") or {}
    organe = ventilation.get("organe") or {}
    groupes = _as_list((organe.get("groupes") or {}).get("groupe"))

    for groupe in groupes:
        decompte_nominatif = (groupe.get("vote") or {}).get("decompteNominatif") or {}
        for key, position in POSITIONS.items():
            for votant in _votants(decompte_nominatif.get(key)):
                yield {
                    "scrutin_uid": scrutin["uid"],
                    "groupe_organe_ref": groupe.get("organeRef"),
                    "acteur_ref": votant.get("acteurRef"),
                    "mandat_ref": votant.get("mandatRef"),
                    "position": position,
                    "par_delegation": votant.get("parDelegation") == "true",
                }


def _mandats(acteur: dict) -> list[dict]:
    return _as_list((acteur.get("mandats") or {}).get("mandat"))


def _mandat_actif_courant(acteur: dict, type_organe: str) -> dict | None:
    """Le mandat actuellement en cours (dateFin nulle) pour un type d'organe
    donné (ex: "ASSEMBLEE" pour le siège de député, "GP" pour le groupe
    politique)."""
    for mandat in _mandats(acteur):
        if mandat.get("typeOrgane") == type_organe and mandat.get("dateFin") is None:
            return mandat
    return None


def load_acteurs(zip_path: Path) -> pd.DataFrame:
    rows = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if "/acteur/" not in f"/{name}" or not name.endswith(".json"):
                continue
            with zf.open(name) as f:
                acteur = json.load(f)["acteur"]
            ident = acteur["etatCivil"]["ident"]

            siege = _mandat_actif_courant(acteur, "ASSEMBLEE")
            lieu = (siege or {}).get("election", {}).get("lieu") or {}
            groupe = _mandat_actif_courant(acteur, "GP")

            rows.append(
                {
                    "acteur_ref": acteur["uid"]["#text"],
                    "civ": ident.get("civ"),
                    "prenom": ident.get("prenom"),
                    "nom": ident.get("nom"),
                    "region": lieu.get("region"),
                    "departement": lieu.get("departement"),
                    "num_departement": lieu.get("numDepartement"),
                    "num_circonscription": lieu.get("numCirco"),
                    "groupe_actuel_ref": (groupe or {}).get("organes", {}).get("organeRef"),
                }
            )
    return pd.DataFrame(rows)


def load_organes(zip_path: Path) -> pd.DataFrame:
    rows = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if "/organe/" not in f"/{name}" or not name.endswith(".json"):
                continue
            with zf.open(name) as f:
                organe = json.load(f)["organe"]
            rows.append(
                {
                    "organe_ref": organe["uid"],
                    "code_type": organe.get("codeType"),
                    "libelle": organe.get("libelle"),
                    "libelle_abrege": organe.get("libelleAbrege"),
                }
            )
    return pd.DataFrame(rows)
