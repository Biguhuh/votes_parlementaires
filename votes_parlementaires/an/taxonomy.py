"""Taxonomie figée des thèmes de scrutins. Source unique de vérité : le
script de classification (`categorize.py`) et les pages générées (onglet
"Catégories") l'importent tous les deux d'ici, pour ne jamais désynchroniser
la liste utilisée pour classer de celle affichée aux lecteurs.

Modifier cette liste change la classification future (nouveaux textes) mais
ne reclasse pas rétroactivement les textes déjà en cache — voir le README.
"""

CATEGORIES = [
    {
        "id": "finances_fiscalite",
        "label": "Finances publiques & fiscalité",
        "description": "Budget de l'État, sécurité sociale, impôts, comptes publics.",
        "color": "#3f6b8a",
    },
    {
        "id": "agriculture_alimentation",
        "label": "Agriculture & alimentation",
        "description": "Exploitations agricoles, souveraineté alimentaire, alimentation des Français.",
        "color": "#7d8a3f",
    },
    {
        "id": "ecologie_energie_climat",
        "label": "Écologie, énergie & climat",
        "description": "Transition énergétique, climat, biodiversité, gestion de l'eau.",
        "color": "#2f8f5b",
    },
    {
        "id": "securite_justice_ordre_public",
        "label": "Sécurité, justice & ordre public",
        "description": "Police, justice pénale, criminalité, prisons, ordre public.",
        "color": "#8a3f3f",
    },
    {
        "id": "sante_fin_de_vie",
        "label": "Santé & fin de vie",
        "description": "Système de santé, maladies, soins palliatifs, aide à mourir.",
        "color": "#a13f7a",
    },
    {
        "id": "travail_economie_entreprises",
        "label": "Travail, économie & entreprises",
        "description": "Emploi, dialogue social, entreprises, régulation économique.",
        "color": "#b98a2e",
    },
    {
        "id": "logement_urbanisme",
        "label": "Logement & urbanisme",
        "description": "Logement, marché locatif, urbanisme, aménagement du territoire.",
        "color": "#6b5a8a",
    },
    {
        "id": "education_enfance_jeunesse",
        "label": "Éducation, enfance & jeunesse",
        "description": "École, protection de l'enfance, jeunesse, vie étudiante.",
        "color": "#3f8a8a",
    },
    {
        "id": "institutions_collectivites_outre_mer",
        "label": "Institutions, collectivités & outre-mer",
        "description": "Élus locaux, collectivités territoriales, statuts d'outre-mer, réforme des institutions.",
        "color": "#8a6a3f",
    },
    {
        "id": "defense_europe_affaires_etrangeres",
        "label": "Défense, Europe & affaires étrangères",
        "description": "Défense nationale, Union européenne, diplomatie, traités internationaux.",
        "color": "#4f5f99",
    },
    {
        "id": "numerique_medias_culture",
        "label": "Numérique, médias & culture",
        "description": "Réseaux sociaux, audiovisuel, presse, patrimoine culturel.",
        "color": "#a15a34",
    },
    {
        "id": "solidarites_droits_sociaux",
        "label": "Solidarités & droits sociaux",
        "description": "Retraites, handicap, précarité, discriminations, droits des victimes.",
        "color": "#3f7a6b",
    },
    {
        "id": "vie_politique_procedure",
        "label": "Vie politique & procédure institutionnelle",
        "description": "Motions de censure, déclarations du Gouvernement, fonctionnement du Parlement.",
        "color": "#7a6f5a",
    },
    {
        "id": "autre",
        "label": "Autre / non classé",
        "description": "Ne correspond clairement à aucune autre catégorie.",
        "color": "#7c8894",
    },
]

CATEGORY_IDS = [c["id"] for c in CATEGORIES]
CATEGORY_LABELS = {c["id"]: c["label"] for c in CATEGORIES}
