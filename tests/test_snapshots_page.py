import json
import re

import pytest

from votes_parlementaires.an.build import scrutins_csv
from votes_parlementaires.config import AN_LEGISLATURE_DEFAULT
from votes_parlementaires.senat.build_votes import scrutins_csv as senat_scrutins_csv
from votes_parlementaires.senat.data import SenatData
from votes_parlementaires.snapshots.page import generate
from votes_parlementaires.webapp.data import ANData

pytestmark = pytest.mark.skipif(
    not scrutins_csv(AN_LEGISLATURE_DEFAULT).exists() or not senat_scrutins_csv().exists(),
    reason="Nécessite les CSV AN et Sénat construits (an.build, senat.build, senat.build_votes).",
)


def test_generate_produces_valid_self_contained_page(tmp_path):
    out = generate(["17", "79"], legislature=AN_LEGISLATURE_DEFAULT, out=tmp_path / "elus-17-79.html")

    assert out.exists()
    html = out.read_text(encoding="utf-8")

    assert not re.findall(r"\[\[[A-Z_]+\]\]", html), "des placeholders n'ont pas été remplacés"

    m = re.search(r'<script id="votes-data" type="application/json">(.*?)</script>', html, re.S)
    assert m is not None
    payload = json.loads(m.group(1))

    # Député·e·s (AN) + sénateur·rice·s (Sénat) en exercice en Charente-Maritime (17) et dans les
    # Deux-Sèvres (79) : les effectifs bougent (élections, démissions), on les relit dans les données.
    deputes = ANData(AN_LEGISLATURE_DEFAULT).deputes_actifs
    senateurs = SenatData().senateurs_actifs
    attendus = int(deputes["num_departement"].isin(["17", "79"]).sum()) + int(
        senateurs["num_departement"].isin(["17", "79"]).sum()
    )
    assert len(payload["deputes"]) == attendus
    for ref, entry in payload["deputes"].items():
        for vote in entry["votes"]:
            assert 0 <= vote["gi"] < len(payload["groups"])

    assert 'id="tab-senateurs"' in html
    assert 'id="panel-senateurs"' in html
