from datetime import date


def current_session_annee(today: date | None = None) -> int:
    """Année de la session sénatoriale en cours. Une session court d'octobre
    à septembre et est numérotée par l'année de son début (ex: la session
    qui commence en octobre 2025 est la session "2025")."""
    today = today or date.today()
    return today.year if today.month >= 10 else today.year - 1
