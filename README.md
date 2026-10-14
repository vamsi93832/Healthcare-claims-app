# Marketplace Claim Denials Analysis

**How often do health insurers deny claims, which ones deny far more than their competitors, and how much of it could be prevented?**

Every insurer selling individual plans on HealthCare.gov has to report its claims, denials and appeals to CMS. This project takes two years of that federal data, covering about 500 million claims a year from up to 206 insurers in 31 states, and turns it into the analysis a health plan's analytics team would hand to leadership: validated KPIs, an insurer benchmark, a breakdown of preventable denials, and an appeals review. It runs on Python, SQL and a Streamlit dashboard.

This is real, public data: the CMS Transparency in Coverage files for 2023 and 2024 claims.

---

## Key findings

1. **One in five claims is denied.** Insurers received 496 million claims in 2024 and denied 101 million, a 20.4% denial rate (down from 20.9% in 2023). Insurers vary widely: the middle half deny between 17% and 27%.
2. **82 insurers deny more than their in-state competitors.** If each matched its competitors' rate, there would be **9.2 million fewer denials a year**, about 9% of all denials. The largest gap is one Florida insurer with 1.6 million excess denials.
3. **Most denials aren't medical decisions.** Process and paperwork problems (administrative errors, missing referrals or prior authorization, eligibility issues) made up **37%** of denial reasons in 2024, up from 33%. Medical necessity decisions were under **5%**. Another 32% is filed under "Other" by the insurers themselves.
4. **Out-of-network claims are twice as likely to be denied.** 37.1% of them were denied in 2024 against 18.7% in network, and out-of-network claims grew from 7.4% to 9.0% of all claims. Out-of-network denials also jumped from 5.8% to 9.8% of the denial reason mix.
5. **Almost nobody appeals, but appeals often win.** Only about 1 in 360 denied claims is appealed, yet a third of appeals (33.6%) are overturned. At several insurers, members win more than 60% of appeals.
6. **Cheaper plans see more denials.** Bronze plans denied 21.0% of claims and Gold plans 18.2%. The pattern holds across HMO, EPO and POS plans, but PPO plans are nearly flat (17.9% Bronze vs 17.4% Gold).

## Recommendations

**For a payment integrity or operations team:** The fastest win is the 37% of denials caused by process problems. Real-time eligibility checks at the point of service, and a prior authorization workflow that flags missing referrals before a claim is submitted, target denials that cost both sides money and are fixable upstream.

**For network and contracting:** Out-of-network claims are growing and denied at twice the rate. Look at where members go out of network most, since those are the gaps where network adequacy is failing.

**For compliance and member experience:** A one-in-three overturn rate means many first-pass denials don't hold up. Insurers in the scorecard with both high excess denials and high appeal overturn rates are the first places to audit denial criteria.

**For data governance:** A third of denials are reported as "Other." Pushing for more specific reason codes would make every analysis above sharper.

---

## KPI definitions

| KPI | Definition |
|---|---|
| Denial rate | Claims denied ÷ claims received, in and out of network combined |
| Peers' rate | The denial rate of every other insurer in the same state, leaving the insurer itself out |
| Excess denials | Insurer's denials − (its claims × peers' rate). Positive means more denials than peers would produce |
| Appeals per 10,000 denials | Internal appeals filed ÷ claims denied × 10,000 |
| Overturn rate | Appeals decided in the member's favor ÷ appeals filed |

Insurers with no claims data (mostly new to the exchange) are left out of every rate rather than counted as zero.

## Data quality

The raw CMS file has two traps that would wreck the numbers if missed. Every check is in `outputs/data_quality.md`, and all 18 pass.

**Insurer totals repeat on every plan row.** Each insurer's claims, denials and appeals are copied onto every plan it sells. Summing the raw file would report **48.6 billion claims instead of 496 million**, a 98x overcount. Insurer totals come only from a deduplicated insurer table, and a grain check confirms the values are identical on every plan row before deduplicating.

**Suppression codes are mixed into the numbers.** CMS uses `*` (not available), `**` (suppressed for small numbers) and `***` (not required). There are over 21,000 of these across the two files. They're treated as missing, never zero, so small insurers don't look like they never deny anything.

Other checks confirm one row per plan, one state per insurer ID, no insurer denying more claims than it received, and that the reported appeal overturn percentages match the recomputed ones. Two findings shaped the analysis:

- **Enrollment isn't an insurer total.** It looks like one, but it varies across an insurer's plans. The grain check caught this, and enrollment is kept at plan level.
- **Denial reasons double count.** They add up to 1.15–1.30x the plan-level denial totals, because a claim can be denied for more than one reason. Reasons are reported only as shares of the mix, never added to denial counts.

---

## The dashboard

`streamlit run app.py` opens six tabs:

| Tab | Who it's for | What it shows |
|---|---|---|
| Overview | Leadership | Headline KPIs with year-over-year change, denial rate by state, network gap, plan design |
| Insurer scorecard | Network and contracting | Every insurer vs its in-state peers, excess denials, biggest year-over-year movers |
| Why claims are denied | Payment integrity | Reason mix by year, grouped into fixable, coverage, and medical decisions |
| Appeals | Compliance, member experience | Appeal rate, overturn rate, insurers that lose the most appeals |
| Data quality | Anyone checking the work | All 18 checks with results |
| SQL answers | Anyone | All ten business questions with the query behind each |

## How it was built

| Step | File | What it does |
|---|---|---|
| 1 | `01_load_and_validate.py` | Reads both CMS files, handles suppression codes, splits insurer, plan and reason data, runs the quality checks |
| 2 | `02_run_sql.py` | Builds the tables in `sql/schema.sql` and answers the questions in `sql/questions.sql` with DuckDB |
| 3 | `app.py` | The Streamlit dashboard |

**Three tables at three grains.** `issuers` (one row per insurer per year), `plans` (one row per plan per year) and `denial_reasons` (one row per plan, year and reason). A shared view, `issuer_metrics`, defines every core measure once, so all ten questions use the same definitions.

**Fair benchmarking.** Each insurer is compared with the rest of its state, leaving itself out, so a dominant insurer can't set its own benchmark. Insurers under 100,000 claims are left out of the scorecard, since a few hundred claims can swing a rate.

**Year labels.** CMS names each file for the plan year it was published in, but the claims inside are two years older. The PY2026 file holds 2024 claims. The mapping lives in one place in step 1, so trends can't shift by accident.

## Run it yourself

In Google Colab:

```python
!git clone https://github.com/vamsi93832/healthcare-claims-app.git
%cd healthcare-claims-app
!pip install -q -r requirements-pipeline.txt

!python 01_load_and_validate.py
!python 02_run_sql.py
```

Locally, run the same two scripts, then `streamlit run app.py`. Both CMS files ship with the repo in `data/raw/`. If they're missing, step 1 downloads them from CMS.

## Project structure

```
healthcare-claims-app/
├── 01_load_and_validate.py
├── 02_run_sql.py
├── app.py                        Streamlit dashboard
├── sql/
│   ├── schema.sql                tables and the shared metrics view
│   └── questions.sql             ten business questions
├── data/raw/                     the two CMS files, as published
├── outputs/                      data quality report and SQL answers (the dashboard reads these)
├── requirements.txt              dashboard only
└── requirements-pipeline.txt     adds openpyxl and DuckDB for the full pipeline
```

## Data source

Centers for Medicare & Medicaid Services, [Transparency in Coverage Public Use Files](https://www.cms.gov/cciio/resources/data-resources/marketplace-puf), PY2025 and PY2026 releases (2023 and 2024 claims), Individual Marketplace medical plans. The data is self-reported by insurers to CMS. CMS notes that denial counts alone aren't a measure of an insurer's quality, since claims can be denied for many legitimate reasons.

---

Built by Vamsi Krishna Chirumalla · [Portfolio](https://vamsikrishnachirumalla.com) · [GitHub](https://github.com/vamsi93832)
