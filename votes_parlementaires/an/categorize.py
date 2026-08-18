"""Classe les textes législatifs des scrutins dans les catégories figées de
`taxonomy.py`, via l'API Claude, avec mise en cache.

Le principe : on n'appelle jamais le LLM sur un texte déjà classé. Le cache
(`categories/<législature>.csv`, versionné dans git) est donc *le* résultat
de classification qui compte — le classer à nouveau ne le change pas. Seuls
les textes réellement nouveaux (nouveaux scrutins depuis le dernier run)
déclenchent un appel API, ce qui rend le processus quasi-intégralement
reproductible d'un passage à l'autre.

Usage :
    echo 'ANTHROPIC_API_KEY=...' > .env   # jamais commité (voir .gitignore)
    python -m votes_parlementaires.an.categorize
    python -m votes_parlementaires.an.categorize --dry-run   # sans appel API
"""

import argparse
import csv
import os
import re
from pathlib import Path

import pandas as pd

from votes_parlementaires.an.build import scrutins_csv
from votes_parlementaires.an.legislature import detect_current_legislature
from votes_parlementaires.an.taxonomy import CATEGORIES, CATEGORY_IDS, CATEGORY_LABELS
from votes_parlementaires.config import ROOT_DIR

CACHE_DIR = Path(__file__).parent / "categories"
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_BATCH_SIZE = 30
FALLBACK_CATEGORY = "autre"

_TEXTE_PAT = re.compile(
    r"(?:de l[a'’]|du|des|au|aux)\s+((?:projet|proposition)s?\s+de\s+(?:loi|résolution européenne).*?)"
    r"(?:\s*\((?:première|nouvelle|deuxième|troisième)\s+lecture\)"
    r"|\s*\(lecture définitive\)|\s*\(commission mixte paritaire\)"
    r"|\s*\(seconde délibération\)"
    r"|\s*\(texte de la commission(?: mixte paritaire)?\)|\.?\s*$)",
    re.IGNORECASE,
)


def extract_texte(titre) -> str | None:
    """Extrait le nom du texte législatif sous-jacent (projet/proposition de
    loi ou de résolution) à partir du titre d'un scrutin, en retirant les
    mentions de procédure (lecture, CMP, seconde délibération...)."""
    if not isinstance(titre, str):
        return None
    if "motion de censure" in titre:
        return "motion de censure"
    if "déclaration du Gouvernement" in titre:
        return "déclaration du Gouvernement"
    m = _TEXTE_PAT.search(titre)
    if not m:
        return None
    return m.group(1).strip().rstrip(".").strip()


def normalize_key(texte: str) -> str:
    t = texte.replace("’", "'").replace("œ", "oe")
    t = re.sub(r"\s+", " ", t).strip().rstrip(".")
    return t.lower()


def _load_dotenv() -> None:
    """Charge un fichier .env à la racine du projet (KEY=VALUE par ligne)
    dans les variables d'environnement, sans écraser une valeur déjà
    définie. Évite une dépendance à python-dotenv pour un seul cas d'usage."""
    dotenv_path = ROOT_DIR / ".env"
    if not dotenv_path.exists():
        return
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def cache_path(legislature: int) -> Path:
    return CACHE_DIR / f"{legislature}.csv"


def load_cache(legislature: int) -> dict[str, str]:
    path = cache_path(legislature)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        return {row["texte_normalise"]: row["categorie_id"] for row in csv.DictReader(f)}


def save_cache(legislature: int, texte_by_key: dict[str, str], categorie_by_key: dict[str, str]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path(legislature), "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["texte_normalise", "texte", "categorie_id", "categorie_label"])
        writer.writeheader()
        for key in sorted(categorie_by_key):
            cid = categorie_by_key[key]
            writer.writerow(
                {
                    "texte_normalise": key,
                    "texte": texte_by_key.get(key, key),
                    "categorie_id": cid,
                    "categorie_label": CATEGORY_LABELS.get(cid, cid),
                }
            )


def distinct_textes(scrutins: pd.DataFrame) -> dict[str, str]:
    """Retourne {clé normalisée: texte original (premier vu)} pour tous les
    textes législatifs distincts référencés par les scrutins fournis."""
    out: dict[str, str] = {}
    for titre in scrutins["titre"]:
        texte = extract_texte(titre)
        if texte is None:
            continue
        key = normalize_key(texte)
        out.setdefault(key, texte)
    return out


def classify_batch(client, model: str, textes: list[str]) -> dict[int, str]:
    numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(textes))
    categories_desc = "\n".join(f"- {c['id']}: {c['label']} — {c['description']}" for c in CATEGORIES)

    tool = {
        "name": "classify_texts",
        "description": "Classe chaque texte législatif fourni dans une catégorie de la taxonomie.",
        "input_schema": {
            "type": "object",
            "properties": {
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "idx": {"type": "integer"},
                            "categorie_id": {"type": "string", "enum": CATEGORY_IDS},
                        },
                        "required": ["idx", "categorie_id"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["classifications"],
            "additionalProperties": False,
        },
        "strict": True,
    }

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        output_config={"effort": "low"},
        system=(
            "Tu classes des textes législatifs français (projets et propositions de loi, "
            "résolutions) dans une taxonomie thématique figée, pour une étude des votes à "
            "l'Assemblée nationale. Choisis pour chaque texte l'unique catégorie qui décrit "
            "le mieux son objet principal. N'utilise 'autre' que si aucune autre catégorie "
            "ne convient clairement.\n\nCatégories disponibles :\n" + categories_desc
        ),
        tools=[tool],
        tool_choice={"type": "tool", "name": "classify_texts"},
        messages=[{"role": "user", "content": f"Textes à classer :\n{numbered}"}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return {c["idx"]: c["categorie_id"] for c in block.input["classifications"]}
    raise RuntimeError("Réponse sans tool_use — impossible d'extraire la classification.")


def run(legislature: int | None = None, model: str = DEFAULT_MODEL, batch_size: int = DEFAULT_BATCH_SIZE, dry_run: bool = False) -> None:
    legislature = legislature or detect_current_legislature()
    scrutins = pd.read_csv(scrutins_csv(legislature), dtype=str)

    textes = distinct_textes(scrutins)
    cache = load_cache(legislature)
    missing_keys = [k for k in textes if k not in cache]

    print(f"Législature {legislature} : {len(scrutins)} scrutins, {len(textes)} textes distincts.")
    print(f"Déjà en cache : {len(cache) - len(cache.keys() - textes.keys())} / {len(textes)}.")
    print(f"À classer : {len(missing_keys)}.")

    if not missing_keys:
        print("Rien à faire, le cache couvre déjà tous les textes.")
        return

    if dry_run:
        print("(--dry-run : pas d'appel API)")
        for k in missing_keys[:10]:
            print(" -", textes[k])
        if len(missing_keys) > 10:
            print(f"   ... et {len(missing_keys) - 10} de plus.")
        return

    import anthropic

    _load_dotenv()
    client = anthropic.Anthropic()
    new_categories: dict[str, str] = {}
    for i in range(0, len(missing_keys), batch_size):
        batch_keys = missing_keys[i : i + batch_size]
        batch_textes = [textes[k] for k in batch_keys]
        print(f"Classification {i + 1}-{i + len(batch_keys)} / {len(missing_keys)}...")
        result = classify_batch(client, model, batch_textes)
        for idx, key in enumerate(batch_keys):
            new_categories[key] = result.get(idx, FALLBACK_CATEGORY)

    cache.update(new_categories)
    save_cache(legislature, textes, cache)
    print(f"Cache mis à jour : {cache_path(legislature)} ({len(cache)} textes classés).")


def load_categorie_map(legislature: int) -> dict[str, str]:
    """Pour un usage en aval (webapp, snapshots) : {clé de texte normalisée:
    categorie_id}, tel que persisté dans le cache versionné."""
    return load_cache(legislature)


def categorize_titre(titre: str, categorie_map: dict[str, str]) -> str:
    """Catégorie d'un scrutin à partir de son titre : extrait le texte
    législatif sous-jacent, cherche sa catégorie dans le cache fourni, et
    retombe sur `FALLBACK_CATEGORY` si le texte n'a pas de match ou n'a pas
    encore été classé (voir `python -m votes_parlementaires.an.categorize`)."""
    texte = extract_texte(titre)
    if texte is None:
        return FALLBACK_CATEGORY
    return categorie_map.get(normalize_key(texte), FALLBACK_CATEGORY)


def main() -> None:
    parser = argparse.ArgumentParser(description="Classe les textes législatifs des scrutins par thème (via l'API Claude, avec cache).")
    parser.add_argument("--legislature", type=int, default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Modèle Claude à utiliser (défaut : {DEFAULT_MODEL}).")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--dry-run", action="store_true", help="N'appelle pas l'API, affiche juste ce qui serait classé.")
    args = parser.parse_args()
    run(legislature=args.legislature, model=args.model, batch_size=args.batch_size, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
