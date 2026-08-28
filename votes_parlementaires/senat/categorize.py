"""Classe les textes législatifs des scrutins du Sénat dans les catégories
figées de `votes_parlementaires.an.taxonomy` — la même taxonomie thématique
que côté Assemblée nationale, un texte de loi relevant du même thème qu'il
soit voté par l'une ou l'autre chambre. Réutilise le moteur de classification
de `votes_parlementaires.an.categorize` (extraction du texte depuis le
titre, appel à l'API Claude, cache), avec son propre cache
(`an/categories/senat.csv`, versionné dans git comme les caches par
législature).

Usage :
    python -m votes_parlementaires.senat.categorize
    python -m votes_parlementaires.senat.categorize --dry-run
"""

import argparse

import pandas as pd

from votes_parlementaires.an.categorize import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MODEL,
    FALLBACK_CATEGORY,
    _load_dotenv,
    cache_path,
    classify_batch,
    distinct_textes,
    load_cache,
    save_cache,
)
from votes_parlementaires.senat.build_votes import scrutins_csv

CACHE_KEY = "senat"


def load_categorie_map() -> dict[str, str]:
    return load_cache(CACHE_KEY)


def run(model: str = DEFAULT_MODEL, batch_size: int = DEFAULT_BATCH_SIZE, dry_run: bool = False) -> None:
    scrutins = pd.read_csv(scrutins_csv(), dtype=str)

    textes = distinct_textes(scrutins)
    cache = load_cache(CACHE_KEY)
    missing_keys = [k for k in textes if k not in cache]

    print(f"Sénat : {len(scrutins)} scrutins, {len(textes)} textes distincts.")
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
    save_cache(CACHE_KEY, textes, cache)
    print(f"Cache mis à jour : {cache_path(CACHE_KEY)} ({len(cache)} textes classés).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classe les textes législatifs des scrutins du Sénat par thème (via l'API Claude, avec cache)."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Modèle Claude à utiliser (défaut : {DEFAULT_MODEL}).")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--dry-run", action="store_true", help="N'appelle pas l'API, affiche juste ce qui serait classé.")
    args = parser.parse_args()
    run(model=args.model, batch_size=args.batch_size, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
