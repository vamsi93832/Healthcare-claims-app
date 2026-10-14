# the dashboard
#
# six tabs, one per audience:
#   overview        -> leadership: the headline numbers and how they moved
#   insurer scorecard -> network/contracting: who denies more than their peers
#   why denied      -> payment integrity: which denials are fixable upstream
#   appeals         -> member advocacy / compliance: who pushes back and who wins
#   data quality    -> anyone checking the work
#   sql answers     -> every question with the query behind it
#
# reads only from outputs/, which is committed, so the live site never has
# to download or reprocess the CMS files when it wakes up
#
#   streamlit run app.py

import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
RED, BLUE, GREY = "#c0392b", "#1f6f8b", "#9aa5b1"

st.set_page_config(page_title="Claim Denials", layout="wide")

if not (OUT / "sql" / "kpi_summary.csv").exists():
    st.error("No results yet. Run 01_load_and_validate.py and 02_run_sql.py first.")
    st.stop()


@st.cache_data
def load():
    sql = {p.stem: pd.read_csv(p) for p in (OUT / "sql").glob("*.csv")}
    return sql, pd.read_csv(OUT / "data_quality_checks.csv")


def sql_blocks():
    # question text and query straight from the sql file
    text = (ROOT / "sql" / "questions.sql").read_text()
    out = {}
    for block in re.split(r"\n(?=-- name: )", text):
        name = re.search(r"-- name: (\w+)", block)
        if name:
            question = re.search(r"-- question: (.+)", block).group(1).strip()
            out[name.group(1)] = (question, block[block.index("\n", block.index("-- question:")):].strip())
    return out


def hbar(df, y, x, title, color=RED, sort="-x", height=260, fmt=".1f"):
    return (alt.Chart(df).mark_bar(color=color)
            .encode(y=alt.Y(f"{y}:N", sort=sort, title=None),
                    x=alt.X(f"{x}:Q", title=title),
                    tooltip=[y, alt.Tooltip(f"{x}:Q", format=fmt)])
            .properties(height=height))


sql, checks = load()
kpi = sql["kpi_summary"].set_index("year")
cur, prev = kpi.loc[2024], kpi.loc[2023]

st.title("Marketplace Claim Denials, 2023–2024")
st.caption("CMS Transparency in Coverage data for every insurer selling individual medical plans on "
           "HealthCare.gov. Insurers report these numbers to CMS themselves.")

overview, scorecard_tab, why_tab, appeals_tab, quality_tab, sql_tab = st.tabs(
    ["Overview", "Insurer scorecard", "Why claims are denied", "Appeals", "Data quality", "SQL answers"])


with overview:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Claims received (2024)", f"{cur['claims_received'] / 1e6:,.0f}M",
              f"{(cur['claims_received'] / prev['claims_received'] - 1):+.1%} vs 2023")
    k2.metric("Claims denied", f"{cur['claims_denied'] / 1e6:,.0f}M",
              f"{(cur['claims_denied'] / prev['claims_denied'] - 1):+.1%} vs 2023", delta_color="inverse")
    k3.metric("Denial rate", f"{cur['denial_rate_pct']:.1f}%",
              f"{cur['denial_rate_pct'] - prev['denial_rate_pct']:+.1f} pts", delta_color="inverse")
    k4.metric("Out-of-network denial rate", f"{cur['out_network_denial_pct']:.1f}%",
              f"{cur['out_network_denial_pct'] - prev['out_network_denial_pct']:+.1f} pts", delta_color="inverse")

    left, right = st.columns(2)
    with left:
        st.markdown("**Denial rate by state, 2024**")
        states = sql["denial_rate_by_state"].fillna({"note": ""})
        st.altair_chart(hbar(states, "state", "denial_rate_2024_pct", "Denial rate (%)", height=520),
                        width="stretch")
        st.caption("States with one or two insurers can swing on a single company. See the SQL tab for the full table.")
    with right:
        st.markdown("**In-network vs out-of-network**")
        net = sql["network_gap"].melt(id_vars="year", value_vars=["in_network_denial_pct", "out_network_denial_pct"],
                                      var_name="network", value_name="rate")
        net["network"] = net["network"].map({"in_network_denial_pct": "In network", "out_network_denial_pct": "Out of network"})
        net["year"] = net["year"].astype(str)
        st.altair_chart(
            alt.Chart(net).mark_bar()
            .encode(x=alt.X("year:N", title=None), xOffset="network:N",
                    y=alt.Y("rate:Q", title="Denial rate (%)"),
                    color=alt.Color("network:N", scale=alt.Scale(range=[BLUE, RED]), title=None),
                    tooltip=["year", "network", alt.Tooltip("rate:Q", format=".1f")])
            .properties(height=240), width="stretch")
        gap = sql["network_gap"].set_index("year").loc[2024]
        st.write(f"An out-of-network claim was **{gap['out_vs_in_ratio']:.1f}x** as likely to be denied in 2024, "
                 f"and out-of-network claims grew to **{gap['out_network_share_of_claims_pct']:.0f}%** of all claims.")

        st.markdown("**Denial rate by plan design, 2024** (plans with plan-level data)")
        design = sql["denials_by_plan_design"]
        order = ["Bronze", "Silver", "Gold", "Platinum"]
        st.altair_chart(
            alt.Chart(design).mark_bar()
            .encode(x=alt.X("metal_level:N", sort=order, title=None), xOffset="plan_type:N",
                    y=alt.Y("denial_rate_pct:Q", title="Denial rate (%)"),
                    color=alt.Color("plan_type:N", title="Plan type"),
                    tooltip=["plan_type", "metal_level", "plans", alt.Tooltip("denial_rate_pct:Q", format=".1f")])
            .properties(height=220), width="stretch")


with scorecard_tab:
    sc = sql["insurer_scorecard"]
    above = sc[sc["excess_denials"] > 0]
    s1, s2, s3 = st.columns(3)
    s1.metric("Insurers compared (100K+ claims)", f"{len(sc)}")
    s2.metric("Deny more than in-state peers", f"{len(above)}")
    s3.metric("Excess denials if they matched peers", f"{above['excess_denials'].sum() / 1e6:.1f}M")
    st.caption("Each insurer is compared with every other insurer in its state, leaving itself out so a "
               "big company can't set its own benchmark. Excess denials = denials above what the peer rate would produce.")

    pick = st.multiselect("State", sorted(sc["state"].unique()))
    view = sc[sc["state"].isin(pick)] if pick else sc
    top = view.head(15).assign(label=lambda d: d["issuer_name"].str.slice(0, 38) + " (" + d["state"] + ")")
    st.altair_chart(hbar(top, "label", "excess_denials", "Excess denials vs in-state peers", fmt=",.0f",
                         height=max(160, 26 * len(top))), width="stretch")
    pct = st.column_config.NumberColumn(format="%.1f%%")
    st.dataframe(view.rename(columns={
        "issuer_name": "Insurer", "state": "State", "claims_received": "Claims",
        "denial_rate_pct": "Denial rate", "state_peers_rate_pct": "Peers' rate", "gap_pts": "Gap (pts)",
        "excess_denials": "Excess denials", "appeal_overturn_pct": "Appeals overturned"}),
        hide_index=True, width="stretch",
        column_config={"Claims": st.column_config.NumberColumn(format="%d"),
                       "Excess denials": st.column_config.NumberColumn(format="%d"),
                       "Denial rate": pct, "Peers' rate": pct, "Appeals overturned": pct})

    st.markdown("**Biggest year-over-year changes**")
    st.dataframe(sql["biggest_movers"], hide_index=True, width="stretch")


with why_tab:
    left, right = st.columns(2)
    with left:
        st.markdown("**Denial reasons, share of all reasons recorded**")
        mix = sql["denial_reason_mix"].melt(id_vars="reason", value_vars=["share_2023_pct", "share_2024_pct"],
                                            var_name="year", value_name="share")
        mix["year"] = mix["year"].str.extract(r"(\d{4})")[0]
        st.altair_chart(
            alt.Chart(mix).mark_bar()
            .encode(y=alt.Y("reason:N", sort=sql["denial_reason_mix"]["reason"].tolist(), title=None),
                    yOffset="year:N", x=alt.X("share:Q", title="Share of denial reasons (%)"),
                    color=alt.Color("year:N", scale=alt.Scale(range=[GREY, RED]), title=None),
                    tooltip=["reason", "year", alt.Tooltip("share:Q", format=".1f")])
            .properties(height=420), width="stretch")
    with right:
        st.markdown("**Grouped the way a payment integrity team would**")
        grp = sql["preventable_denials"]
        st.altair_chart(hbar(grp, "category", "share_2024_pct", "Share of 2024 denial reasons (%)",
                             sort=None, height=200), width="stretch")
        proc = grp.set_index("category").iloc[0]
        med = grp[grp["category"].str.contains("Medical")].iloc[0]
        st.write(f"**{proc['share_2024_pct']:.0f}%** of denial reasons in 2024 were process or paperwork problems "
                 f"(up from {proc['share_2023_pct']:.0f}%): administrative errors, missing referrals or prior "
                 f"authorization, and eligibility. Only **{med['share_2024_pct']:.0f}%** were medical necessity decisions.")
        st.info("A claim can be denied for more than one reason, so these are shares of all reasons recorded, "
                "not counts of denied claims. About a third are filed under \"Other\" by the insurers themselves.")


with appeals_tab:
    f = sql["appeals_funnel"].set_index("year")
    a24, a23 = f.loc[2024], f.loc[2023]
    a1, a2, a3 = st.columns(3)
    a1.metric("Appeals per 10,000 denials", f"{a24['appeals_per_10k_denials']:.0f}",
              f"{a24['appeals_per_10k_denials'] - a23['appeals_per_10k_denials']:+.0f} vs 2023")
    a2.metric("Appeals filed (2024)", f"{a24['appeals_filed']:,.0f}")
    a3.metric("Appeals won by the member", f"{a24['overturn_pct']:.0f}%",
              f"{a24['overturn_pct'] - a23['overturn_pct']:+.1f} pts", delta_color="off")
    st.write(f"Only about **1 in {10000 / a24['appeals_per_10k_denials']:,.0f}** denied claims is appealed, "
             f"yet about **1 in {100 / a24['overturn_pct']:.0f}** appeals wins. "
             "For the denials people do challenge, the insurer's first answer is often wrong.")

    st.markdown("**Insurers that lose the most appeals** (100+ appeals filed, 2024)")
    st.dataframe(sql["appeal_overturns_by_insurer"], hide_index=True, width="stretch",
                 column_config={"overturn_pct": st.column_config.NumberColumn("Overturned", format="%.1f%%"),
                                "denial_rate_pct": st.column_config.NumberColumn("Denial rate", format="%.1f%%")})


with quality_tab:
    st.subheader("Checks run before any number was trusted")
    st.dataframe(checks.assign(passed=checks["passed"].map({True: "Pass", False: "FAIL"})),
                 hide_index=True, width="stretch",
                 column_config={"check": "Check", "passed": "Result", "detail": st.column_config.TextColumn("Detail", width="large")})
    st.markdown("""
**The two that mattered most**

- **Insurer totals appear on every plan row.** Summing the raw file would report about 49 *billion*
  claims instead of 496 million, a 98x overcount. Insurer totals come only from a deduplicated insurer table.
- **CMS codes like `*` and `**` mean missing or suppressed, never zero.** Treating them as zero would
  make small insurers look like they never deny anything. They're excluded from rates instead.
""")


with sql_tab:
    blocks = sql_blocks()
    names = [n for n in blocks if n in sql]
    q = st.selectbox("Question", names, format_func=lambda n: blocks[n][0])
    st.dataframe(sql[q], hide_index=True, width="stretch")
    with st.expander("Show the SQL"):
        st.code(blocks[q][1], language="sql")
