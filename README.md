# votes_parlementaires

Consultation des votes des députés et sénateurs français de la mandature actuelle,
à partir des sources open data officielles.

- **Assemblée nationale** : implémenté. Source officielle
  [data.assemblee-nationale.fr](https://data.assemblee-nationale.fr/travaux-parlementaires/votes)
  (export JSON des scrutins + référentiel des acteurs/organes).
- **Sénat** : pas encore implémenté. L'open data officiel du Sénat
  ([data.senat.fr](https://data.senat.fr/donnees/)) n'expose pas de jeu de
  données "scrutins publics" structuré ; NosSénateurs.fr est fermé (archive
  2004-2023 seulement, rien sur la mandature actuelle). La seule voie
  restante est un scraper sur les pages HTML
  [senat.fr/scrutin-public](https://www.senat.fr/scrutin-public/scr2025.html)
  (aucun export XML/CSV/JSON disponible côté Sénat).

## Startup the project

```bash
pyenv virtualenv 3.10.6 votes_parlementaires
pyenv local votes_parlementaires
pip install -r requirements.txt
```

## Assemblée nationale

### Construire / mettre à jour les données

```bash
python -m votes_parlementaires.an.build
```

Ce script :
1. Détecte la législature en cours (`votes_parlementaires/an/legislature.py`) en
   sondant le portail open data de l'AN — pas besoin de mettre à jour un
   numéro codé en dur d'une mandature à l'autre.
2. Télécharge les 3 sources officielles dans `data/raw/an/<législature>/` :
   - `Scrutins.json.zip` — un fichier JSON par scrutin (positions de vote de
     chaque député).
   - `AMO40_deputes_actifs_mandats_actifs_organes_divises.json.zip` —
     référentiel des députés/organes actuellement actifs.
   - `AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip` —
     référentiel complet (historique), pour couvrir les députés ayant voté
     puis quitté leur mandat en cours de législature (démission, décès,
     nomination au Gouvernement...).
3. Construit 4 CSV dans `data/processed/an/<législature>/`.

Chaque législature écrit dans son propre dossier numéroté : relancer le
script après un changement de mandature crée `data/*/an/18/` sans jamais
écraser les données de `data/*/an/17/`.

Options :
- `--skip-download` : reconstruit les CSV à partir des zips déjà présents
  dans `data/raw/an/<législature>/`, sans retélécharger.
- `--legislature N` : force le numéro de législature au lieu de le détecter
  automatiquement (utile pour reconstruire une législature passée).

### Fichiers produits (`data/processed/an/<législature>/`)

| Fichier | Contenu |
|---|---|
| `scrutins.csv` | 1 ligne par scrutin : titre, date, résultat, décompte global des voix |
| `votes.csv` | 1 ligne par (scrutin × député) : position (pour/contre/abstention/non-votant), vote par délégation |
| `acteurs.csv` | référentiel des députés (nom, prénom, département/circonscription du siège actif, groupe politique actuel) |
| `organes.csv` | référentiel des groupes politiques / organes |
| `_meta.json` | date de construction (`built_at`), utilisée par les pages figées (voir plus bas) pour afficher une date fiable |

`votes.csv` référence `scrutins.csv` par `scrutin_uid`, `acteurs.csv` par
`acteur_ref`, et `organes.csv` par `groupe_organe_ref`.

### Page web de consultation

Une petite appli locale (Flask + JS vanilla) pour parcourir les votes : recherche
de députés par nom/département/circonscription, vue par groupe politique, et
recherche de scrutins avec le détail des votes individuels par scrutin.

```bash
python -m votes_parlementaires.webapp.app
```

Ouvre ensuite [http://localhost:5050](http://localhost:5050) dans ton
navigateur (les CSV de la législature détectée doivent déjà exister, voir
section précédente). C'est un serveur de dev Flask (`debug=True`) : arrête-le
avec Ctrl+C, ou en tuant le process qui écoute sur le port 5050.

Cette appli charge tout `data/processed/an/<législature>/` en mémoire (pandas)
au démarrage — pas de base de données, pas de dépendance réseau après le
premier chargement.

### Pages figées (données gelées, partageables hors-ligne)

Pour partager un instantané autonome (un seul fichier HTML, sans serveur ni
réseau) listant les député·e·s de certains départements avec leurs
statistiques de vote et l'historique complet de leurs scrutins :

```bash
python -m votes_parlementaires.snapshots.deputes --departements 17 79
```

Écrit `data/snapshots/an/<législature>/deputes-17-79.html`. Les données sont
entièrement embarquées dans le fichier (pas d'appel réseau à l'ouverture) et
la page affiche la date à laquelle les CSV source ont été construits (voir
`votes_parlementaires/an/meta.py`), pour qu'on sache toujours de quand datent
les chiffres affichés.

Pour chaque député·e, la fiche (accessible en cliquant sur son nom) liste tous
ses scrutins avec un filtre par mot-clé et un filtre par plage de dates (du /
au), pour retrouver rapidement un scrutin précis dans un historique qui peut
compter plusieurs milliers d'entrées.

À relancer après un `python -m votes_parlementaires.an.build` pour régénérer
la page avec des données fraîches — le fichier de sortie est simplement
écrasé, sans accumulation de versions datées.

Options :
- `--departements` : liste de numéros de département (défaut : `17 79`).
- `--legislature` : forcer une législature (défaut : la plus récente déjà
  construite dans `data/processed/an/`).
- `--out` : chemin de sortie personnalisé.
