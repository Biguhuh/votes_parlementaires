import urllib.error

import pandas as pd
import pytest

from votes_parlementaires.senat import build_mandats, build_votes

PANNE = urllib.error.URLError("[Errno 101] Network is unreachable")


@pytest.fixture
def processed_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(build_votes, "senat_processed_dir", lambda: tmp_path)
    monkeypatch.setattr(build_mandats, "senat_processed_dir", lambda: tmp_path)
    return tmp_path


def test_build_votes_keeps_previous_csv_when_senat_is_unreachable(processed_dir, monkeypatch, capsys):
    (processed_dir / "scrutins.csv").write_text("scrutin_ref,annee_session,numero\nsenat-2025-1,2025,1\n")
    (processed_dir / "votes.csv").write_text("scrutin_ref,senateur_ref,position\nsenat-2025-1,14213J,pour\n")
    avant = {f.name: f.read_text() for f in processed_dir.iterdir()}

    def injoignable(annee):
        raise PANNE

    monkeypatch.setattr(build_votes, "list_scrutin_numeros", injoignable)

    build_votes.main([2026])  # ne doit pas lever

    assert {f.name: f.read_text() for f in processed_dir.iterdir()} == avant, "CSV modifiés ou fichier temporaire laissé"
    assert "::warning::" in capsys.readouterr().out


def test_build_votes_still_fails_without_previous_data(processed_dir, monkeypatch):
    def injoignable(annee):
        raise PANNE

    monkeypatch.setattr(build_votes, "list_scrutin_numeros", injoignable)

    with pytest.raises(urllib.error.URLError):
        build_votes.main([2026])


def test_build_mandats_stops_fetching_after_first_network_failure(processed_dir, monkeypatch):
    pd.DataFrame({"senateur_ref": ["A", "B", "C"]}).to_csv(processed_dir / "senateurs.csv", index=False)
    pd.DataFrame({"senateur_ref": ["A", "B", "C"], "slug": ["a", "b", "c"]}).to_csv(
        processed_dir / "senateurs_slugs.csv", index=False
    )
    monkeypatch.setattr(build_mandats, "senateurs_csv", lambda: processed_dir / "senateurs.csv")
    monkeypatch.setattr(build_mandats, "senateurs_slugs_csv", lambda: processed_dir / "senateurs_slugs.csv")
    appels = []

    def injoignable(slug, skip_download):
        appels.append(slug)
        raise PANNE

    monkeypatch.setattr(build_mandats, "_fetch_senateur_html", injoignable)

    build_mandats.main()  # ne doit pas lever

    assert appels == ["a"], "après la première panne, les fiches suivantes ne doivent plus être tentées"
