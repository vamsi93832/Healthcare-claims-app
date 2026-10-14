# Step 2 - answer the business questions in SQL
#
# loads the three tidy tables into DuckDB, builds the schema and the shared
# metrics view in sql/schema.sql, runs every question in sql/questions.sql,
# and saves each answer to outputs/sql/ for the dashboard.
#
# DuckDB because it's real SQL from a single file with no server to set up,
# so it runs the same in Colab as on a laptop
#
#   python 02_run_sql.py

import re
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).parent
PROCESSED = ROOT / "data" / "processed"
SQL_DIR = ROOT / "sql"
OUT = ROOT / "outputs" / "sql"


def questions():
    # each block starts with "-- name:" and "-- question:", so the .sql file
    # stays the single source of truth and the dashboard shows the exact query
    text = (SQL_DIR / "questions.sql").read_text()
    out = []
    for block in re.split(r"\n(?=-- name: )", text):
        name = re.search(r"-- name: (\w+)", block)
        if not name:
            continue
        question = re.search(r"-- question: (.+)", block).group(1).strip()
        body = block[block.index("\n", block.index("-- question:")):].strip()
        out.append((name.group(1), question, body))
    return out


if __name__ == "__main__":
    if not (PROCESSED / "issuers.csv").exists():
        raise SystemExit("run 01_load_and_validate.py first")
    OUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    # issuer IDs and plan IDs are codes, not numbers. reading them as text keeps
    # leading zeros and stops anyone from accidentally averaging them
    ids = {"issuer_id": str, "plan_id": str}
    con.register("issuers_src", pd.read_csv(PROCESSED / "issuers.csv", dtype=ids))
    con.register("plans_src", pd.read_csv(PROCESSED / "plans.csv", dtype=ids))
    con.register("reasons_src", pd.read_csv(PROCESSED / "denial_reasons.csv", dtype=ids))
    con.execute((SQL_DIR / "schema.sql").read_text())

    for name, question, sql in questions():
        result = con.execute(sql).df()
        result.to_csv(OUT / f"{name}.csv", index=False)
        with pd.option_context("display.width", 200, "display.max_columns", 20):
            print(f"\n{question}\n{result.head(10).to_string(index=False)}")

    print(f"\nsaved {len(questions())} answers to outputs/sql/")
