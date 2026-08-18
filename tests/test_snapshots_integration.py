import json
import re

import pytest

from votes_parlementaires.an.build import scrutins_csv
from votes_parlementaires.config import AN_LEGISLATURE_DEFAULT
from votes_parlementaires.snapshots.deputes import generate

pytestmark = pytest.mark.skipif(
    not scrutins_csv(AN_LEGISLATURE_DEFAULT).exists(),
    reason="Nécessite les CSV construits (python -m votes_parlementaires.an.build).",
)


def test_generate_produces_valid_self_contained_page(tmp_path):
    out = generate(["17", "79"], legislature=AN_LEGISLATURE_DEFAULT, out=tmp_path / "deputes-17-79.html")

    assert out.exists()
    html = out.read_text(encoding="utf-8")

    assert not re.findall(r"\[\[[A-Z_]+\]\]", html), "des placeholders n'ont pas été remplacés"

    m = re.search(r'<script id="votes-data" type="application/json">(.*?)</script>', html, re.S)
    assert m is not None
    payload = json.loads(m.group(1))

    assert len(payload["deputes"]) == 8
    for ref, entry in payload["deputes"].items():
        for vote in entry["votes"]:
            assert 0 <= vote["gi"] < len(payload["groups"])
