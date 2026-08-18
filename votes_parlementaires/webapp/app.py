from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from votes_parlementaires.webapp.data import ANData

STATIC_DIR = Path(__file__).parent / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
data = ANData()


def paginate(df: pd.DataFrame, page: int, per_page: int):
    page = max(1, page)
    per_page = max(1, min(per_page, 200))
    start = (page - 1) * per_page
    end = start + per_page
    return df.iloc[start:end], len(df)


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/meta")
def meta():
    return jsonify(
        {
            "legislature": data.legislature,
            "nb_scrutins": len(data.scrutins),
            "nb_deputes": len(data.deputes_actifs),
        }
    )


@app.get("/api/deputes")
def list_deputes():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 30, type=int)
    df = data.search_deputes(q)
    page_df, total = paginate(df, page, per_page)
    return jsonify({"total": total, "results": data.deputes_to_dicts(page_df)})


@app.get("/api/deputes/<acteur_ref>")
def depute_detail(acteur_ref):
    record = data.depute(acteur_ref)
    if record is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(record)


@app.get("/api/deputes/<acteur_ref>/votes")
def depute_votes(acteur_ref):
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 30, type=int)
    df = data.depute_votes(acteur_ref, q)
    page_df, total = paginate(df, page, per_page)
    return jsonify({"total": total, "results": page_df.to_dict("records")})


@app.get("/api/groupes")
def list_groupes():
    return jsonify(data.groupes())


@app.get("/api/groupes/<organe_ref>")
def groupe_detail(organe_ref):
    record = data.groupe(organe_ref)
    if record is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(record)


@app.get("/api/scrutins")
def list_scrutins():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 30, type=int)
    df = data.search_scrutins(q)
    page_df, total = paginate(df, page, per_page)
    return jsonify(
        {
            "total": total,
            "results": page_df.drop(columns=["_search"]).astype(object).where(
                pd.notnull(page_df.drop(columns=["_search"])), None
            ).to_dict("records"),
        }
    )


@app.get("/api/scrutins/<scrutin_uid>")
def scrutin_detail(scrutin_uid):
    record = data.scrutin(scrutin_uid)
    if record is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(record)


def main():
    app.run(debug=True, port=5050)


if __name__ == "__main__":
    main()
