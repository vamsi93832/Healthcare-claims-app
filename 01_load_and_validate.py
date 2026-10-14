# Step 1 - load the CMS claims denial files and check them before trusting them
#
# the CMS Transparency in Coverage file is one wide sheet per year, and it
# mixes two levels of detail in the same row: insurer totals (claims, denials,
# appeals) repeated on every plan, plus plan-level denial reasons. this script
# splits that into three tidy tables at the right grain, turns the CMS
# suppression codes into real missing values, and writes a data quality
# report so every number downstream can be traced back to a check.
#
#   python 01_load_and_validate.py

from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "outputs"

# CMS labels files by the plan year they were published for, but the claims
# inside are from two years earlier. PY2026 = 2024 claims. getting this wrong
# would shift every trend by two years, so the mapping lives in one place
FILES = {
    2024: ("tic_puf_py2026.xlsx", "Transparency 2026 - Ind QHP", 2026),
    2023: ("tic_puf_py2025.xlsx", "Transparency 2025 - Ind QHP", 2025),
}
URL = "https://download.cms.gov/marketplace-puf/{py}/transparency-in-coverage-puf.zip"

# what the CMS codes mean (from the legend in the file). none of them are zero,
# so they all become missing. treating "suppressed" as 0 would make small
# insurers look like they never deny anything
SPECIAL_CODES = {"*": "not available", "**": "suppressed (small numbers)",
                 "***": "not required for plan type", "N/A": "new to the exchange"}

ISSUER_COLS = {
    "Issuer_Claims_Received_In_Network": "received_in_network",
    "Issuer_Claims_Received_Out_of_Network": "received_out_network",
    "Issuer_Claims_Denied_In_Network": "denied_in_network",
    "Issuer_Claims_Denied_Out_of_Network": "denied_out_network",
    "Issuer_Claims_Resubmitted_In_Network": "resubmitted_in_network",
    "Issuer_Claims_Resubmitted_Out_of_Network": "resubmitted_out_network",
    "Issuer_Internal_Appeals_Filed": "internal_appeals_filed",
    "Issuer_Number_Internal_Appeals_Overturned": "internal_appeals_overturned",
    "Issuer_Percent_Internal_Appeals_Overturned": "reported_internal_overturn_pct",
    "Issuer_External_Appeals_Filed": "external_appeals_filed",
    "Issuer_Number_External_Appeals_Overturned": "external_appeals_overturned",
}
PLAN_COLS = {
    "Plan_Number_Claims_Received_In_Network": "received_in_network",
    "Plan_Number_Claims_Received_Out_of_Network": "received_out_network",
    "Plan_Number_Claims_Denied_In_Network": "denied_in_network",
    "Plan_Number_Claims_Denied_Out_of_Network": "denied_out_network",
    # enrollment looks like an insurer total (no Plan_ prefix, same blanks as the
    # insurer columns) but it changes from plan to plan, so it's plan-level.
    # the grain check below is what caught it
    "Average Monthly Enrollment": "avg_monthly_enrollment",
    "Average Monthly Disenrollment": "avg_monthly_disenrollment",
}
# CMS column -> plain-language reason (their spelling of "Enrolle" kept in the source name)
REASONS = {
    "Plan_Number_Claims_Denied_Referral_Required": "Referral or prior authorization required",
    "Plan_Number_Claims_Denied_Due_To_Out_Of_Network": "Out-of-network provider",
    "Plan_Number_Claims_Denied_Services_Excluded": "Service not covered by plan",
    "Plan_Number_Claims_Denied_Not_Medically_Necessary_Excluding_Behavioral_Health": "Not medically necessary (medical)",
    "Plan_Number_Claims_Denied_Not_Medically_Necessary_Behavioral_Health_Only": "Not medically necessary (behavioral health)",
    "Plan_Number_Claims_Denied_Due_To_Enrolle_Benefit_Limit_Reached": "Benefit limit reached",
    "Plan_Number_Claims_Denied_Due_To_Member_Not_Covered": "Member not covered",
    "Plan_Number_Claims_Denied_Due_To_Investigational_Experimental_Cosmetic_Proceduce": "Experimental or cosmetic",
    "Plan_Number_Claims_Denied_Due_To_Administrative_Reason": "Administrative",
    "Plan_Number_Claims_Denied_Other": "Other",
}


def read_year(year):
    file, sheet, py = FILES[year]
    path = RAW / file
    if not path.exists():
        # the repo ships both files, so this only runs if someone deleted them
        import zipfile
        zpath = RAW / f"tic_py{py}.zip"
        print(f"downloading PY{py} from CMS")
        urlretrieve(URL.format(py=py), zpath)
        with zipfile.ZipFile(zpath) as z:
            xlsx = next(n for n in z.namelist() if n.lower().endswith(".xlsx"))
            path.write_bytes(z.read(xlsx))

    # the header isn't on the first row (there's a title and a legend above it),
    # and it moved between years before, so find it instead of hardcoding it
    top = pd.read_excel(path, sheet_name=sheet, header=None, nrows=10)
    header_row = next(i for i in range(10) if str(top.iloc[i, 1]).strip() == "Exchange_Type")
    # read everything as text first. the numbers are mixed with codes like "**",
    # and letting pandas guess types would silently turn them into NaN without a trace
    df = pd.read_excel(path, sheet_name=sheet, header=header_row, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df.insert(0, "year", year)
    return df


def to_number(s):
    return pd.to_numeric(s.str.strip().str.replace(",", ""), errors="coerce")


def split_tables(raw):
    # insurer table: one row per insurer per year
    issuers = raw.drop_duplicates(["year", "Issuer_ID"])[
        ["year", "State", "Exchange_Type", "Issuer_ID", "Issuer_Name",
         "Is_Issuer_New_to_Exchange?(Yes_or_No)"] + list(ISSUER_COLS)].rename(columns={
        "State": "state", "Exchange_Type": "exchange_type", "Issuer_ID": "issuer_id",
        "Issuer_Name": "issuer_name", "Is_Issuer_New_to_Exchange?(Yes_or_No)": "new_to_exchange",
        **ISSUER_COLS})
    for c in ISSUER_COLS.values():
        issuers[c] = to_number(issuers[c])
    plan_counts = raw.groupby(["year", "Issuer_ID"]).size().rename("plans_offered")
    issuers = issuers.merge(plan_counts, left_on=["year", "issuer_id"], right_index=True)

    # plan table: one row per plan per year, plan-level claims only
    plans = raw[["year", "Plan_ID", "Issuer_ID", "State", "Plan_Type", "Metal_Level"] + list(PLAN_COLS)].rename(
        columns={"Plan_ID": "plan_id", "Issuer_ID": "issuer_id", "State": "state",
                 "Plan_Type": "plan_type", "Metal_Level": "metal_level", **PLAN_COLS})
    for c in PLAN_COLS.values():
        plans[c] = to_number(plans[c])

    # denial reasons: long format, one row per plan per reason
    reasons = raw[["year", "Plan_ID"] + list(REASONS)].melt(
        id_vars=["year", "Plan_ID"], var_name="source_column", value_name="raw_value")
    reasons["reason"] = reasons["source_column"].map(REASONS)
    reasons["denied_claims"] = to_number(reasons["raw_value"])
    reasons = reasons.rename(columns={"Plan_ID": "plan_id"})[["year", "plan_id", "reason", "denied_claims"]]
    return issuers, plans, reasons


def quality_checks(raw, issuers, plans, reasons):
    checks = []

    def check(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    for year in sorted(raw["year"].unique()):
        r = raw[raw["year"] == year]
        i = issuers[issuers["year"] == year]
        p = plans[plans["year"] == year]
        tag = f"[{year}]"

        check(f"{tag} One row per plan", r["Plan_ID"].is_unique,
              f"{len(r):,} rows, {r['Plan_ID'].nunique():,} unique plan IDs")

        # the grain check that matters most: insurer totals must be identical on
        # every plan row of that insurer, or deduplicating would pick one at random
        varying = r.groupby("Issuer_ID")[list(ISSUER_COLS)].nunique(dropna=False).max().max()
        check(f"{tag} Insurer totals identical on every plan row", varying == 1,
              f"max distinct values of an insurer field within one insurer: {varying}")

        states_per_issuer = r.groupby("Issuer_ID")["State"].nunique().max()
        check(f"{tag} Each insurer ID belongs to one state", states_per_issuer == 1,
              f"max states per insurer ID: {states_per_issuer}")

        received = i["received_in_network"].fillna(0) + i["received_out_network"].fillna(0)
        naive = (to_number(r["Issuer_Claims_Received_In_Network"]).fillna(0)
                 + to_number(r["Issuer_Claims_Received_Out_of_Network"]).fillna(0)).sum()
        check(f"{tag} Insurer totals counted once, not once per plan", True,
              f"summing every plan row would report {naive:,.0f} claims; deduplicated it's "
              f"{received.sum():,.0f} ({naive / received.sum():.0f}x overcount avoided)")

        denied = i["denied_in_network"].fillna(0) + i["denied_out_network"].fillna(0)
        bad = (denied > received).sum()
        check(f"{tag} No insurer denies more claims than it received", bad == 0,
              f"{bad} insurers fail")

        no_claims = i["received_in_network"].isna().sum()
        check(f"{tag} Insurers with claims data", True,
              f"{len(i) - no_claims} of {len(i)} insurers report claims; {no_claims} have none "
              "(mostly new to the exchange) and are left out of rates, not counted as zero")

        has_plan = p["received_in_network"].notna().sum()
        check(f"{tag} Plans with plan-level claims data", True,
              f"{has_plan:,} of {len(p):,} plans ({has_plan / len(p):.0%}); denial reasons only exist for these")

        # reasons don't add up to the plan's total denials, so a claim can carry
        # more than one reason. that means reasons are shares of the mix, never
        # something to add to the denial total
        rs = reasons[reasons["year"] == year]["denied_claims"].sum()
        pd_total = (p["denied_in_network"].fillna(0) + p["denied_out_network"].fillna(0)).sum()
        check(f"{tag} Denial reasons vs plan denial totals", True,
              f"reasons sum to {rs:,.0f} vs {pd_total:,.0f} plan denials ({rs / pd_total:.2f}x). "
              "Some claims are denied for more than one reason, so reasons are reported as shares only")

        # recompute the overturn rate instead of trusting the reported percent
        filed, over = i["internal_appeals_filed"], i["internal_appeals_overturned"]
        both = filed.gt(0) & over.notna() & i["reported_internal_overturn_pct"].notna()
        diff = ((over[both] / filed[both] * 100) - i.loc[both, "reported_internal_overturn_pct"]).abs()
        check(f"{tag} Reported appeal overturn % matches recomputed", (diff <= 1).mean() >= 0.95,
              f"{(diff <= 1).sum()} of {both.sum()} insurers within 1 point; recomputed values used downstream")

    codes = []
    for col in list(ISSUER_COLS) + list(PLAN_COLS) + list(REASONS):
        for code, meaning in SPECIAL_CODES.items():
            n = (raw[col].str.strip() == code).sum()
            if n:
                codes.append({"column": col, "code": code, "meaning": meaning, "rows": int(n)})
    return pd.DataFrame(checks), pd.DataFrame(codes)


def write_report(checks, codes):
    lines = ["# Data quality report", "",
             "Source: CMS Transparency in Coverage PUF, Individual Marketplace medical plans (Ind QHP sheet). "
             "Self-reported by insurers to CMS.", "",
             "| Check | Result | Detail |", "|---|---|---|"]
    for _, c in checks.iterrows():
        lines.append(f"| {c['check']} | {'Pass' if c['passed'] else 'FAIL'} | {c['detail']} |")
    lines += ["", "## CMS special codes, treated as missing (never as zero)", "",
              "| Code | Meaning | Rows across all columns |", "|---|---|---|"]
    for code, g in codes.groupby("code"):
        lines.append(f"| `{code}` | {g['meaning'].iloc[0]} | {g['rows'].sum():,} |")
    (OUT / "data_quality.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)

    raw = pd.concat([read_year(y) for y in sorted(FILES)], ignore_index=True)
    issuers, plans, reasons = split_tables(raw)
    checks, codes = quality_checks(raw, issuers, plans, reasons)

    issuers.to_csv(PROCESSED / "issuers.csv", index=False)
    plans.to_csv(PROCESSED / "plans.csv", index=False)
    reasons.to_csv(PROCESSED / "denial_reasons.csv", index=False)
    checks.to_csv(OUT / "data_quality_checks.csv", index=False)
    write_report(checks, codes)

    print(f"insurers: {len(issuers):,} insurer-years | plans: {len(plans):,} | reason rows: {len(reasons):,}")
    print(f"\ndata quality: {checks['passed'].sum()} of {len(checks)} checks passed")
    for _, c in checks[~checks["passed"]].iterrows():
        print(f"  FAILED: {c['check']} -> {c['detail']}")
    print("\nsaved data/processed/ and outputs/data_quality.md")
