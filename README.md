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

### Classification des scrutins par thème

L'export officiel de l'AN ne contient **aucun tag thématique** (vérifié
directement sur `Scrutins.json` — seuls un titre en texte libre et parfois
une référence de dossier législatif sont disponibles). Le module
`votes_parlementaires.an.categorize` comble ce manque :

1. Il extrait le texte législatif sous-jacent (projet/proposition de loi ou
   de résolution) du titre de chaque scrutin, via
   `votes_parlementaires.an.categorize.extract_texte`.
2. Il classe chaque texte distinct dans une catégorie de la taxonomie figée
   de `votes_parlementaires/an/taxonomy.py` (finances publiques, agriculture
   & alimentation, écologie/énergie/climat, sécurité & justice, santé,
   institutions, etc. — 14 catégories, voir l'onglet **Catégories** des
   pages figées).
3. Le résultat est mis en cache dans
   `votes_parlementaires/an/categories/<législature>.csv` (**versionné dans
   git**, à la différence du reste de `data/` — voir l'exception dans
   `.gitignore`), avec pour clé le texte législatif normalisé.

**Pourquoi 251 textes classés pour 8434 scrutins (17e législature) ?** Un
scrutin, c'est un vote unique ; un texte de loi donne lieu à *des dizaines*
de scrutins — un par amendement, par article, plus un par étape de la
procédure (première lecture, commission mixte paritaire, seconde
délibération...). Le budget 2026 (PLF) à lui seul totalise 925 scrutins pour
un seul texte. Classer par texte plutôt que par scrutin évite de payer et de
classer 8434 fois la même chose, et garantit que tous les votes d'un même
texte reçoivent la même catégorie.

Clé API à créer sur [platform.claude.com](https://platform.claude.com) (le
compte Claude.ai et l'API sont facturés séparément — une clé API ne marche
pas avec un abonnement Claude.ai). Soit exportée dans le shell, soit dans un
fichier `.env` à la racine du projet (jamais commité, voir `.gitignore`) :

```bash
echo 'ANTHROPIC_API_KEY=...' > .env
python -m votes_parlementaires.an.categorize
```

Le point clé : un texte déjà présent dans le cache **n'est jamais reclassé**
— seuls les textes réellement nouveaux (nouveaux scrutins depuis le dernier
passage) déclenchent un appel à l'API Claude. Le classement est donc stable
à quasiment 100% d'un passage à l'autre, puisque l'essentiel du corpus vient
du cache et non d'un nouvel appel au LLM. `--dry-run` affiche ce qui serait
classé sans appeler l'API (utile pour vérifier l'extraction des textes sans
consommer de crédits).

La taxonomie elle-même (`taxonomy.py`) est figée volontairement, mais **pas
immuable** : rien n'empêche de la modifier plus tard (ajouter/renommer/
fusionner une catégorie) si l'usage montre qu'elle ne colle plus. Deux
choses à savoir en la modifiant :
- Ça change le classement des *futurs* textes seulement — le cache déjà
  écrit n'est **pas** reclassé rétroactivement. Pour reclasser l'existant
  avec la nouvelle taxonomie, supprimer les lignes concernées (ou tout le
  fichier `categories/<législature>.csv`) puis relancer `categorize.py`.
- Chaque catégorie a une couleur (`color`, un hex) utilisée à la fois dans
  l'onglet **Catégories** et sur les tags affichés à côté de chaque groupe
  de scrutins — en ajouter une nouvelle veut dire lui choisir aussi une
  couleur.

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
ses scrutins, **regroupés par texte de loi** (voir section précédente — un
texte donne lieu à des dizaines de scrutins) plutôt qu'à plat : chaque
groupe affiche le nom du texte, son tag de catégorie coloré, et le nombre de
scrutins qu'il contient, avec le détail (date, amendement/article,
position, résultat) en dessous. Un filtre par mot-clé et un filtre par
plage de dates (du / au) permettent de retrouver rapidement un scrutin ou
un texte précis dans un historique qui peut compter plusieurs milliers
d'entrées. Si `categorize.py` n'a jamais été lancé, tout tombe dans un
groupe "Autre / non classé" — les tags de catégorie ne demandent aucune
action supplémentaire une fois le cache peuplé, ils sont lus directement
depuis `categories/<législature>.csv` à la génération de la page.

La page a un second onglet, **Catégories**, qui affiche la taxonomie de
`votes_parlementaires/an/taxonomy.py` (voir section précédente) avec la
couleur de chaque catégorie.

À relancer après un `python -m votes_parlementaires.an.build` pour régénérer
la page avec des données fraîches — le fichier de sortie est simplement
écrasé, sans accumulation de versions datées.

Options :
- `--departements` : liste de numéros de département (défaut : `17 79`).
- `--legislature` : forcer une législature (défaut : la plus récente déjà
  construite dans `data/processed/an/`).
- `--out` : chemin de sortie personnalisé.

## Tests

```bash
pytest
```

Couvre l'extraction des textes législatifs (`categorize.py`), la taxonomie,
et la génération des pages figées (`snapshots/deputes.py`, y compris le
regroupement des scrutins et les couleurs de catégorie). Le test
d'intégration bout-en-bout (`test_snapshots_integration.py`) se saute
automatiquement si les CSV de la 17e législature n'ont pas encore été
construits (`python -m votes_parlementaires.an.build`).
