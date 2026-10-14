-- business questions about marketplace claim denials.
-- each block has a name (the output file) and the question it answers, so the
-- dashboard can show the exact query next to its result.
-- standard SQL tested in DuckDB; runs on Snowflake, Postgres or BigQuery with
-- little change (QUANTILE_CONT would be PERCENTILE_CONT elsewhere)


-- name: kpi_summary
-- question: What are the headline denial and appeal numbers, and how did they move year over year?
SELECT
    year,
    COUNT(*)                                                           AS insurers_reporting,
    SUM(claims_received)                                               AS claims_received,
    SUM(claims_denied)                                                 AS claims_denied,
    ROUND(100.0 * SUM(claims_denied) / SUM(claims_received), 2)        AS denial_rate_pct,
    ROUND(100.0 * SUM(denied_in_network) / SUM(received_in_network), 2) AS in_network_denial_pct,
    ROUND(100.0 * SUM(denied_out_network) / SUM(received_out_network), 2) AS out_network_denial_pct,
    -- appeal measures only count insurers that report BOTH appeals filed and
    -- overturned, the same population as the appeals funnel below. the first
    -- version mixed in insurers with missing appeal data, and the overturn
    -- rate here came out a point off from the funnel's
    SUM(CASE WHEN has_appeals THEN internal_appeals_filed END)         AS appeals_filed,
    ROUND(10000.0 * SUM(CASE WHEN has_appeals THEN internal_appeals_filed END)
        / SUM(CASE WHEN has_appeals THEN claims_denied END), 1)        AS appeals_per_10k_denials,
    ROUND(100.0 * SUM(CASE WHEN has_appeals THEN internal_appeals_overturned END)
        / SUM(CASE WHEN has_appeals THEN internal_appeals_filed END), 1) AS appeal_overturn_pct
FROM (
    SELECT *, internal_appeals_filed IS NOT NULL AND internal_appeals_overturned IS NOT NULL AS has_appeals
    FROM issuer_metrics
) m
GROUP BY year
ORDER BY year;


-- name: denial_rate_by_state
-- question: Which states have the highest denial rates, and where did they change most?
WITH by_state AS (
    SELECT year, state,
           COUNT(*)            AS insurers,
           SUM(claims_received) AS claims_received,
           SUM(claims_denied)   AS claims_denied
    FROM issuer_metrics
    GROUP BY year, state
)
SELECT
    cur.state,
    cur.insurers,
    cur.claims_received,
    ROUND(100.0 * cur.claims_denied / cur.claims_received, 1)                      AS denial_rate_2024_pct,
    ROUND(100.0 * prev.claims_denied / prev.claims_received, 1)                    AS denial_rate_2023_pct,
    ROUND(100.0 * cur.claims_denied / cur.claims_received
        - 100.0 * prev.claims_denied / prev.claims_received, 1)                    AS change_pts,
    -- states with one or two insurers can swing on a single company's reporting,
    -- so they're flagged rather than hidden
    CASE WHEN cur.insurers <= 2 THEN 'Few insurers, read with care' ELSE '' END   AS note
FROM by_state cur
LEFT JOIN by_state prev ON prev.state = cur.state AND prev.year = 2023
WHERE cur.year = 2024
ORDER BY denial_rate_2024_pct DESC;


-- name: insurer_scorecard
-- question: Which insurers deny far more than their in-state competitors, and how many extra denials is that?
-- each insurer is compared with the rest of its state (itself left out), so a big
-- insurer can't drag its own benchmark up. "excess denials" is how many fewer
-- denials it would have at its competitors' rate. small insurers are left out
-- because a few hundred claims can swing a rate wildly
WITH state_totals AS (
    SELECT year, state, SUM(claims_received) AS st_received, SUM(claims_denied) AS st_denied, COUNT(*) AS st_insurers
    FROM issuer_metrics
    GROUP BY year, state
)
SELECT
    m.issuer_name,
    m.state,
    m.claims_received,
    ROUND(100.0 * m.claims_denied / m.claims_received, 1)                                   AS denial_rate_pct,
    ROUND(100.0 * (s.st_denied - m.claims_denied) / (s.st_received - m.claims_received), 1) AS state_peers_rate_pct,
    ROUND(100.0 * m.claims_denied / m.claims_received
        - 100.0 * (s.st_denied - m.claims_denied) / (s.st_received - m.claims_received), 1) AS gap_pts,
    ROUND(m.claims_denied - m.claims_received
        * (s.st_denied - m.claims_denied) / (s.st_received - m.claims_received), 0)        AS excess_denials,
    ROUND(100.0 * m.internal_appeals_overturned / NULLIF(m.internal_appeals_filed, 0), 1)  AS appeal_overturn_pct
FROM issuer_metrics m
JOIN state_totals s ON s.year = m.year AND s.state = m.state
WHERE m.year = 2024
  AND m.claims_received >= 100000
  AND s.st_insurers >= 2          -- need at least one competitor to compare against
ORDER BY excess_denials DESC;


-- name: biggest_movers
-- question: Which insurers changed their denial rate the most between 2023 and 2024?
SELECT
    cur.issuer_name,
    cur.state,
    cur.claims_received                                                AS claims_2024,
    ROUND(100.0 * prev.claims_denied / prev.claims_received, 1)        AS denial_rate_2023_pct,
    ROUND(100.0 * cur.claims_denied / cur.claims_received, 1)          AS denial_rate_2024_pct,
    ROUND(100.0 * cur.claims_denied / cur.claims_received
        - 100.0 * prev.claims_denied / prev.claims_received, 1)        AS change_pts
FROM issuer_metrics cur
JOIN issuer_metrics prev ON prev.issuer_id = cur.issuer_id AND prev.year = 2023
WHERE cur.year = 2024
  AND cur.claims_received >= 100000 AND prev.claims_received >= 100000
ORDER BY ABS(change_pts) DESC
LIMIT 20;


-- name: denial_reason_mix
-- question: Why are claims denied, and did the reasons shift between years?
-- shares of all reasons recorded. a claim can carry more than one reason, so
-- these are shares of the mix, never counts to add to the denial total
WITH totals AS (
    SELECT year, reason, SUM(denied_claims) AS n
    FROM denial_reasons
    WHERE denied_claims IS NOT NULL
    GROUP BY year, reason
)
SELECT
    t24.reason,
    ROUND(100.0 * t24.n / SUM(t24.n) OVER (), 1)   AS share_2024_pct,
    ROUND(100.0 * t23.n / SUM(t23.n) OVER (), 1)   AS share_2023_pct,
    ROUND(100.0 * t24.n / SUM(t24.n) OVER ()
        - 100.0 * t23.n / SUM(t23.n) OVER (), 1)   AS change_pts
FROM totals t24
JOIN totals t23 ON t23.reason = t24.reason AND t23.year = 2023
WHERE t24.year = 2024
ORDER BY share_2024_pct DESC;


-- name: preventable_denials
-- question: How much of the denial volume is paperwork and process rather than a medical decision?
-- grouping the CMS reasons the way a payment integrity team would: process
-- problems can be fixed upstream (eligibility checks, prior auth workflows,
-- clean claim submission); coverage and medical decisions mostly can't
WITH grouped AS (
    SELECT
        year,
        CASE
            WHEN reason IN ('Administrative', 'Referral or prior authorization required', 'Member not covered')
                THEN '1. Process or paperwork (fixable upstream)'
            WHEN reason IN ('Out-of-network provider', 'Service not covered by plan', 'Benefit limit reached', 'Experimental or cosmetic')
                THEN '2. Coverage and benefit design'
            WHEN reason LIKE 'Not medically necessary%'
                THEN '3. Medical necessity decision'
            ELSE '4. Other / unspecified'
        END AS category,
        SUM(denied_claims) AS n
    FROM denial_reasons
    WHERE denied_claims IS NOT NULL
    GROUP BY 1, 2
)
SELECT
    category,
    ROUND(100.0 * SUM(CASE WHEN year = 2024 THEN n END) / SUM(SUM(CASE WHEN year = 2024 THEN n END)) OVER (), 1) AS share_2024_pct,
    ROUND(100.0 * SUM(CASE WHEN year = 2023 THEN n END) / SUM(SUM(CASE WHEN year = 2023 THEN n END)) OVER (), 1) AS share_2023_pct
FROM grouped
GROUP BY category
ORDER BY category;


-- name: network_gap
-- question: How much more likely is an out-of-network claim to be denied?
SELECT
    year,
    ROUND(100.0 * SUM(denied_in_network) / SUM(received_in_network), 1)   AS in_network_denial_pct,
    ROUND(100.0 * SUM(denied_out_network) / SUM(received_out_network), 1) AS out_network_denial_pct,
    ROUND((1.0 * SUM(denied_out_network) / SUM(received_out_network))
        / (1.0 * SUM(denied_in_network) / SUM(received_in_network)), 2)    AS out_vs_in_ratio,
    ROUND(100.0 * SUM(received_out_network) / SUM(claims_received), 1)    AS out_network_share_of_claims_pct
FROM issuer_metrics
WHERE received_out_network IS NOT NULL AND denied_out_network IS NOT NULL
GROUP BY year
ORDER BY year;


-- name: appeals_funnel
-- question: Of every 10,000 denied claims, how many are appealed, and how many of those win?
SELECT
    year,
    SUM(claims_denied)                                                          AS denied_claims,
    SUM(internal_appeals_filed)                                                 AS appeals_filed,
    ROUND(10000.0 * SUM(internal_appeals_filed) / SUM(claims_denied), 1)        AS appeals_per_10k_denials,
    SUM(internal_appeals_overturned)                                            AS appeals_overturned,
    ROUND(100.0 * SUM(internal_appeals_overturned) / SUM(internal_appeals_filed), 1) AS overturn_pct
FROM issuer_metrics
-- only insurers that report both numbers, so the rates aren't mixing populations
WHERE internal_appeals_filed IS NOT NULL AND internal_appeals_overturned IS NOT NULL
GROUP BY year
ORDER BY year;


-- name: appeal_overturns_by_insurer
-- question: Which insurers lose the most appeals? A high overturn rate suggests denials that shouldn't have happened.
SELECT
    issuer_name,
    state,
    internal_appeals_filed                                                     AS appeals_filed,
    internal_appeals_overturned                                                AS overturned,
    ROUND(100.0 * internal_appeals_overturned / internal_appeals_filed, 1)     AS overturn_pct,
    ROUND(100.0 * claims_denied / claims_received, 1)                          AS denial_rate_pct
FROM issuer_metrics
WHERE year = 2024
  AND internal_appeals_filed >= 100        -- enough appeals for the rate to mean something
  AND internal_appeals_overturned IS NOT NULL
ORDER BY overturn_pct DESC
LIMIT 20;


-- name: denials_by_plan_design
-- question: Do denial rates differ by plan type and metal level?
-- plan-level claims only exist for about 60% of plans, so this is a sample;
-- the insurer-level totals above cover everyone
SELECT
    plan_type,
    metal_level,
    COUNT(*)                                                                        AS plans,
    SUM(received_in_network + COALESCE(received_out_network, 0))                     AS claims_received,
    ROUND(100.0 * SUM(denied_in_network + COALESCE(denied_out_network, 0))
        / SUM(received_in_network + COALESCE(received_out_network, 0)), 1)          AS denial_rate_pct
FROM plans
WHERE year = 2024
  AND received_in_network IS NOT NULL AND denied_in_network IS NOT NULL
GROUP BY plan_type, metal_level
HAVING SUM(received_in_network + COALESCE(received_out_network, 0)) >= 500000
ORDER BY plan_type, denial_rate_pct DESC;
