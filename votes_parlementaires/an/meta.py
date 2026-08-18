import json
from datetime import date, datetime, timezone

from votes_parlementaires.config import an_processed_dir


def meta_path(legislature: int):
    return an_processed_dir(legislature) / "_meta.json"


def write_build_meta(legislature: int) -> None:
    """Enregistre la date de construction des CSV, pour que les pages générées
    à partir de ces données (snapshots) puissent afficher une date fiable
    plutôt que la date du jour où la page a été régénérée."""
    meta = {"built_at": datetime.now(timezone.utc).isoformat()}
    meta_path(legislature).write_text(json.dumps(meta), encoding="utf-8")


def read_build_date(legislature: int) -> date | None:
    """Date (sans heure) de la dernière construction des CSV pour cette
    législature, ou None si le fichier de métadonnées n'existe pas encore
    (données construites avant l'introduction de ce mécanisme)."""
    path = meta_path(legislature)
    if not path.exists():
        return None
    meta = json.loads(path.read_text(encoding="utf-8"))
    return datetime.fromisoformat(meta["built_at"]).date()
