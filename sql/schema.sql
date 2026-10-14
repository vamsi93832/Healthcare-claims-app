-- three tables at three grains. 02_run_sql.py loads them from data/processed/
--
--   issuers         one row per insurer per year: claims, denials, appeals
--   plans           one row per plan per year: plan-level claims and enrollment
--   denial_reasons  one row per plan per year per denial reason
--
-- the raw CMS file repeats insurer totals on every plan row, so the insurer
-- table is the ONLY place insurer totals come from. joining it to plans and
-- then summing would bring the overcount right back

CREATE TABLE issuers AS SELECT * FROM issuers_src;
CREATE TABLE plans AS SELECT * FROM plans_src;
CREATE TABLE denial_reasons AS SELECT * FROM reasons_src;

-- one place to define the core measures, so every question below uses the
-- same definitions. insurers with no claims data are excluded rather than
-- treated as zero
CREATE VIEW issuer_metrics AS
SELECT
    year, state, issuer_id, issuer_name, exchange_type, plans_offered,
    received_in_network + COALESCE(received_out_network, 0)          AS claims_received,
    denied_in_network + COALESCE(denied_out_network, 0)              AS claims_denied,
    received_in_network, received_out_network,
    denied_in_network, denied_out_network,
    internal_appeals_filed, internal_appeals_overturned
FROM issuers
WHERE received_in_network IS NOT NULL
  AND denied_in_network IS NOT NULL
  AND received_in_network > 0;
