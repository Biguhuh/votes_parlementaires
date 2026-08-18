from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"

# Dernière législature connue : sert de point de départ à la détection
# automatique (votes_parlementaires.an.legislature) et de repli si celle-ci
# échoue (pas de réseau, etc).
AN_LEGISLATURE_DEFAULT = 17


def an_raw_dir(legislature: int) -> Path:
    """Dossier des fichiers bruts téléchargés, namespacé par législature :
    une future législature (18, ...) écrit dans son propre dossier sans
    jamais écraser les données de la législature précédente."""
    return RAW_DIR / "an" / str(legislature)


def an_processed_dir(legislature: int) -> Path:
    """Dossier des CSV construits, namespacé par législature (voir an_raw_dir)."""
    return PROCESSED_DIR / "an" / str(legislature)


def an_snapshots_dir(legislature: int) -> Path:
    """Dossier des pages HTML figées (données gelées, partageables hors-ligne),
    namespacée par législature (voir an_raw_dir)."""
    return SNAPSHOTS_DIR / "an" / str(legislature)
