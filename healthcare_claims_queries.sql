-- ============================================================================
-- HEALTHCARE CLAIMS ANALYTICS - SQL QUERIES
-- Elevance Health Claims Analysis
-- ============================================================================

-- Query 1: Overall Claims Summary
-- Shows approval rate and financial metrics
SELECT 
    COUNT(*) as total_claims,
    SUM(CASE WHEN claim_status = 'Approved' THEN 1 ELSE 0 END) as approved_claims,
    SUM(CASE WHEN claim_status = 'Denied' THEN 1 ELSE 0 END) as denied_claims,
    ROUND(100.0 * SUM(CASE WHEN claim_status = 'Approved' THEN 1 ELSE 0 END) / COUNT(*), 2) as approval_rate_pct,
    ROUND(SUM(billed_amount), 2) as total_billed,
    ROUND(SUM(allowed_amount), 2) as total_allowed,
    ROUND(SUM(paid_amount), 2) as total_paid,
    ROUND(100.0 * SUM(paid_amount) / SUM(allowed_amount), 2) as payment_ratio_pct
FROM claims;


-- Query 2: Claims by Provider Type
-- Analyzes denial patterns across different provider types
SELECT 
    p.provider_type,
    COUNT(c.claim_id) as claim_count,
    SUM(CASE WHEN c.claim_status = 'Approved' THEN 1 ELSE 0 END) as approved,
    SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) as denied,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) / COUNT(c.claim_id), 2) as denial_rate_pct,
    ROUND(SUM(c.allowed_amount), 2) as total_allowed,
    ROUND(SUM(c.paid_amount), 2) as total_paid
FROM claims c
INNER JOIN providers p ON c.provider_id = p.provider_id
GROUP BY p.provider_type
ORDER BY denial_rate_pct DESC;


-- Query 3: Top Denial Reasons
-- Identifies most common reasons for claim denials
SELECT 
    denial_reason,
    COUNT(*) as denial_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM claims WHERE claim_status = 'Denied'), 2) as percentage,
    ROUND(SUM(allowed_amount), 2) as total_amount,
    ROUND(AVG(allowed_amount), 2) as avg_amount
FROM claims
WHERE claim_status = 'Denied'
GROUP BY denial_reason
ORDER BY denial_count DESC;


-- Query 4: Claims Processing Performance
-- Tracks how quickly claims are processed
SELECT 
    claim_status,
    COUNT(*) as claim_count,
    ROUND(AVG(days_to_process), 1) as avg_days,
    MIN(days_to_process) as min_days,
    MAX(days_to_process) as max_days,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_to_process), 1) as median_days
FROM claims
GROUP BY claim_status
ORDER BY avg_days DESC;


-- Query 5: Denial Analysis by State
-- Geographic analysis of denial patterns
SELECT 
    p.state,
    COUNT(c.claim_id) as claim_count,
    SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) as denied_count,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) / COUNT(c.claim_id), 2) as denial_rate_pct,
    ROUND(SUM(c.allowed_amount), 2) as total_allowed,
    ROUND(SUM(c.paid_amount), 2) as total_paid
FROM claims c
INNER JOIN providers p ON c.provider_id = p.provider_id
GROUP BY p.state
ORDER BY denial_rate_pct DESC;


-- Query 6: High-Risk Providers
-- Identifies providers with high denial rates requiring attention
SELECT 
    p.provider_id,
    p.provider_name,
    p.provider_type,
    COUNT(c.claim_id) as claim_count,
    SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) as denied,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) / COUNT(c.claim_id), 2) as denial_rate_pct,
    ROUND(SUM(c.allowed_amount), 2) as total_allowed
FROM claims c
INNER JOIN providers p ON c.provider_id = p.provider_id
GROUP BY p.provider_id, p.provider_name, p.provider_type
HAVING COUNT(c.claim_id) >= 50
ORDER BY denial_rate_pct DESC
LIMIT 20;


-- Query 7: Appeal Outcome Analysis
-- Shows success rate of appeals for overturning denials
SELECT 
    a.appeal_status,
    COUNT(*) as appeal_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM appeals), 2) as percentage,
    ROUND(AVG(DATEDIFF(DAY, a.appeal_date, CURRENT_DATE)), 1) as avg_days_pending
FROM appeals a
GROUP BY a.appeal_status
ORDER BY appeal_count DESC;


-- Query 8: Claims Processing Trend by Month
-- Shows claims volume and approval trends over time
SELECT 
    DATE_TRUNC('month', c.claim_date) as claim_month,
    COUNT(*) as total_claims,
    SUM(CASE WHEN c.claim_status = 'Approved' THEN 1 ELSE 0 END) as approved,
    SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) as denied,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Approved' THEN 1 ELSE 0 END) / COUNT(*), 2) as approval_rate_pct,
    ROUND(SUM(c.billed_amount), 2) as total_billed,
    ROUND(SUM(c.paid_amount), 2) as total_paid
FROM claims c
GROUP BY DATE_TRUNC('month', c.claim_date)
ORDER BY claim_month DESC;


-- Query 9: Network vs Out-of-Network Comparison
-- Compares approval rates for network and out-of-network providers
SELECT 
    p.network_status,
    COUNT(c.claim_id) as claim_count,
    SUM(CASE WHEN c.claim_status = 'Approved' THEN 1 ELSE 0 END) as approved,
    SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) as denied,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) / COUNT(c.claim_id), 2) as denial_rate_pct,
    ROUND(SUM(c.allowed_amount), 2) as total_allowed,
    ROUND(SUM(c.paid_amount), 2) as total_paid,
    ROUND(AVG(c.days_to_process), 1) as avg_processing_days
FROM claims c
INNER JOIN providers p ON c.provider_id = p.provider_id
GROUP BY p.network_status;


-- Query 10: Member Analytics - High Claim Users
-- Identifies members with frequent claims
SELECT 
    m.member_id,
    m.member_name,
    m.plan_type,
    COUNT(c.claim_id) as claim_count,
    ROUND(SUM(c.allowed_amount), 2) as total_allowed,
    ROUND(SUM(c.paid_amount), 2) as total_paid,
    SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) as denied_count,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Approved' THEN 1 ELSE 0 END) / COUNT(c.claim_id), 2) as approval_rate_pct
FROM claims c
INNER JOIN members m ON c.member_id = m.member_id
GROUP BY m.member_id, m.member_name, m.plan_type
HAVING COUNT(c.claim_id) >= 10
ORDER BY claim_count DESC
LIMIT 30;


-- Query 11: Procedure Code Analysis
-- Analyzes claims by procedure code to identify patterns
SELECT 
    c.procedure_code,
    COUNT(*) as claim_count,
    SUM(CASE WHEN c.claim_status = 'Approved' THEN 1 ELSE 0 END) as approved,
    SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) as denied,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) / COUNT(*), 2) as denial_rate_pct,
    ROUND(AVG(c.allowed_amount), 2) as avg_allowed,
    ROUND(SUM(c.allowed_amount), 2) as total_allowed
FROM claims c
GROUP BY c.procedure_code
ORDER BY denial_rate_pct DESC;


-- Query 12: Plan Type Performance
-- Compares claims metrics across different plan types
SELECT 
    m.plan_type,
    COUNT(c.claim_id) as claim_count,
    SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) as denied,
    ROUND(100.0 * SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) / COUNT(c.claim_id), 2) as denial_rate_pct,
    ROUND(AVG(c.allowed_amount), 2) as avg_allowed_amount,
    ROUND(AVG(c.days_to_process), 1) as avg_processing_days
FROM claims c
INNER JOIN members m ON c.member_id = m.member_id
GROUP BY m.plan_type
ORDER BY denial_rate_pct DESC;


-- ============================================================================
-- INDEXES FOR PERFORMANCE OPTIMIZATION
-- ============================================================================

CREATE INDEX idx_claims_status ON claims(claim_status);
CREATE INDEX idx_claims_member ON claims(member_id);
CREATE INDEX idx_claims_provider ON claims(provider_id);
CREATE INDEX idx_claims_date ON claims(claim_date);
CREATE INDEX idx_claims_denial ON claims(claim_status, denial_reason);

CREATE INDEX idx_providers_type ON providers(provider_type);
CREATE INDEX idx_providers_state ON providers(state);
CREATE INDEX idx_providers_network ON providers(network_status);

CREATE INDEX idx_members_plan ON members(plan_type);
CREATE INDEX idx_members_state ON members(state);

CREATE INDEX idx_appeals_status ON appeals(appeal_status);
CREATE INDEX idx_appeals_claim ON appeals(claim_id);

-- ============================================================================
-- END OF QUERIES
-- ============================================================================
