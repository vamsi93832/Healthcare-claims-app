#!/usr/bin/env python3
"""
Healthcare Claims Analysis
Analyzes claims data for denial patterns, trends, and insights
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*80)
print("HEALTHCARE CLAIMS ANALYSIS")
print("="*80)

# Load datasets
print("\nLoading data files...")
providers = pd.read_csv('providers.csv')
members = pd.read_csv('members.csv')
claims = pd.read_csv('claims.csv')
line_items = pd.read_csv('line_items.csv')
appeals = pd.read_csv('appeals.csv')

print(f"✓ Loaded {len(providers)} providers")
print(f"✓ Loaded {len(members)} members")
print(f"✓ Loaded {len(claims)} claims")
print(f"✓ Loaded {len(line_items)} line items")
print(f"✓ Loaded {len(appeals)} appeals")

# Convert date columns
members['date_of_birth'] = pd.to_datetime(members['date_of_birth'])
members['effective_date'] = pd.to_datetime(members['effective_date'])
claims['claim_date'] = pd.to_datetime(claims['claim_date'])
claims['service_date'] = pd.to_datetime(claims['service_date'])
appeals['appeal_date'] = pd.to_datetime(appeals['appeal_date'])

# ============================================================================
# ANALYSIS 1: CLAIMS APPROVAL METRICS
# ============================================================================
print("\n" + "-"*80)
print("ANALYSIS 1: CLAIMS APPROVAL METRICS")
print("-"*80)

approval_summary = claims['claim_status'].value_counts()
approval_pct = (approval_summary / len(claims) * 100).round(2)

print(f"\nClaim Status Distribution:")
for status in ['Approved', 'Denied', 'Pending']:
    count = approval_summary.get(status, 0)
    pct = approval_pct.get(status, 0)
    print(f"  {status:12s}: {count:6,} claims ({pct:5.1f}%)")

# Calculate financial impact
total_billed = claims['billed_amount'].sum()
total_allowed = claims['allowed_amount'].sum()
total_paid = claims['paid_amount'].sum()

print(f"\nFinancial Summary:")
print(f"  Total Billed:        ${total_billed:>15,.2f}")
print(f"  Total Allowed:       ${total_allowed:>15,.2f}")
print(f"  Total Paid:          ${total_paid:>15,.2f}")
print(f"  Denial Amount:       ${(claims[claims['claim_status']=='Denied']['allowed_amount'].sum()):>15,.2f}")
print(f"  Payment Ratio:       {total_paid/total_allowed*100:>15.1f}%")

# ============================================================================
# ANALYSIS 2: TOP DENIAL REASONS
# ============================================================================
print("\n" + "-"*80)
print("ANALYSIS 2: TOP DENIAL REASONS")
print("-"*80)

denial_analysis = claims[claims['claim_status'] == 'Denied'].groupby('denial_reason').size().reset_index(name='count')
denial_analysis = denial_analysis.sort_values('count', ascending=False).head(10)
denial_analysis['percentage'] = (denial_analysis['count'] / denial_analysis['count'].sum() * 100).round(1)

print("\nTop Denial Reasons:")
for idx, row in denial_analysis.iterrows():
    print(f"  {row['denial_reason']:30s}: {row['count']:5,} ({row['percentage']:5.1f}%)")

# ============================================================================
# ANALYSIS 3: DENIAL RATE BY PROVIDER TYPE
# ============================================================================
print("\n" + "-"*80)
print("ANALYSIS 3: DENIAL RATE BY PROVIDER TYPE")
print("-"*80)

claims_with_provider = claims.merge(providers[['provider_id', 'provider_type']], on='provider_id')

provider_analysis = claims_with_provider.groupby('provider_type').agg({
    'claim_id': 'count',
    'paid_amount': 'sum',
}).reset_index()
provider_analysis.columns = ['provider_type', 'total_claims', 'total_paid']

provider_denial = claims_with_provider[claims_with_provider['claim_status'] == 'Denied'].groupby('provider_type').size().reset_index(name='denied_claims')
provider_analysis = provider_analysis.merge(provider_denial, on='provider_type', how='left')
provider_analysis['denied_claims'] = provider_analysis['denied_claims'].fillna(0)
provider_analysis['denial_rate'] = (provider_analysis['denied_claims'] / provider_analysis['total_claims'] * 100).round(1)

print("\nDenial Rate by Provider Type:")
for idx, row in provider_analysis.iterrows():
    print(f"  {row['provider_type']:12s}: {row['denial_rate']:5.1f}% ({int(row['denied_claims']):,} of {int(row['total_claims']):,})")

# ============================================================================
# ANALYSIS 4: GEOGRAPHIC ANALYSIS
# ============================================================================
print("\n" + "-"*80)
print("ANALYSIS 4: GEOGRAPHIC ANALYSIS")
print("-"*80)

claims_with_provider_state = claims.merge(providers[['provider_id', 'state']], on='provider_id')

state_analysis = claims_with_provider_state.groupby('state').agg({
    'claim_id': 'count',
    'allowed_amount': 'sum',
}).reset_index()
state_analysis.columns = ['state', 'claim_count', 'total_allowed']

state_denial = claims_with_provider_state[claims_with_provider_state['claim_status'] == 'Denied'].groupby('state').size().reset_index(name='denied')
state_analysis = state_analysis.merge(state_denial, on='state', how='left')
state_analysis['denied'] = state_analysis['denied'].fillna(0)
state_analysis['denial_rate'] = (state_analysis['denied'] / state_analysis['claim_count'] * 100).round(1)
state_analysis = state_analysis.sort_values('denial_rate', ascending=False)

print("\nTop States by Denial Rate:")
for idx, row in state_analysis.head(5).iterrows():
    print(f"  {row['state']}: {row['denial_rate']:5.1f}% ({int(row['denied']):,} denials, ${row['total_allowed']/1e6:5.1f}M)")

# ============================================================================
# ANALYSIS 5: CLAIMS PROCESSING TIME
# ============================================================================
print("\n" + "-"*80)
print("ANALYSIS 5: CLAIMS PROCESSING TIME")
print("-"*80)

avg_processing_time = claims['days_to_process'].mean()
median_processing_time = claims['days_to_process'].median()

print(f"\nProcessing Time Statistics:")
print(f"  Average:             {avg_processing_time:8.1f} days")
print(f"  Median:              {median_processing_time:8.1f} days")
print(f"  Min:                 {claims['days_to_process'].min():8.0f} days")
print(f"  Max:                 {claims['days_to_process'].max():8.0f} days")

# Processing time by status
print(f"\nAverage Processing Time by Status:")
for status in ['Approved', 'Denied', 'Pending']:
    avg = claims[claims['claim_status'] == status]['days_to_process'].mean()
    print(f"  {status:12s}: {avg:7.1f} days")

# ============================================================================
# ANALYSIS 6: APPEALS ANALYSIS
# ============================================================================
print("\n" + "-"*80)
print("ANALYSIS 6: APPEALS ANALYSIS")
print("-"*80)

if len(appeals) > 0:
    total_appeals = len(appeals)
    appeal_status_dist = appeals['appeal_status'].value_counts()
    
    print(f"\nTotal Appeals:       {total_appeals:,}")
    
    for status in ['Approved', 'Denied', 'Pending']:
        count = appeal_status_dist.get(status, 0)
        pct = (count / total_appeals * 100)
        print(f"  {status:12s}: {count:5,} ({pct:5.1f}%)")
    
    # Appeal reversal rate
    reversals = len(appeals[(appeals['appeal_status'] == 'Approved')])
    reversal_rate = (reversals / total_appeals * 100)
    print(f"\nAppeal Reversal Rate: {reversal_rate:.1f}%")
else:
    print("\nNo appeals data available")

# ============================================================================
# ANALYSIS 7: HIGH-RISK CLAIMS
# ============================================================================
print("\n" + "-"*80)
print("ANALYSIS 7: HIGH-RISK CLAIMS IDENTIFICATION")
print("-"*80)

# Identify claims with high denial risk
high_risk_reasons = ['Pre-authorization Required', 'Out of Network', 'Incomplete Documentation']
high_risk_claims = claims[claims['denial_reason'].isin(high_risk_reasons)]

print(f"\nHigh-Risk Claims Identified: {len(high_risk_claims):,}")
print(f"Percentage of Total: {len(high_risk_claims)/len(claims)*100:.1f}%")
print(f"Amount at Risk: ${high_risk_claims['allowed_amount'].sum():,.2f}")

# ============================================================================
# ANALYSIS 8: SAVE DETAILED RESULTS
# ============================================================================
print("\n" + "-"*80)
print("SAVING ANALYSIS RESULTS")
print("-"*80)

# Summary report by provider
provider_summary = claims_with_provider.groupby('provider_id').agg({
    'claim_id': 'count',
    'allowed_amount': 'sum',
    'paid_amount': 'sum',
    'days_to_process': 'mean',
}).reset_index()
provider_summary.columns = ['provider_id', 'claim_count', 'total_allowed', 'total_paid', 'avg_processing_days']

denied_by_provider = claims_with_provider[claims_with_provider['claim_status'] == 'Denied'].groupby('provider_id').size().reset_index(name='denied_count')
provider_summary = provider_summary.merge(denied_by_provider, on='provider_id', how='left')
provider_summary['denied_count'] = provider_summary['denied_count'].fillna(0)
provider_summary['denial_rate'] = (provider_summary['denied_count'] / provider_summary['claim_count'] * 100).round(1)

provider_summary = provider_summary.sort_values('denial_rate', ascending=False)
provider_summary.to_csv('provider_analysis_summary.csv', index=False)
print("✓ Saved provider_analysis_summary.csv")

# Summary by denial reason
denial_summary = claims[claims['claim_status'] == 'Denied'].groupby('denial_reason').agg({
    'claim_id': 'count',
    'allowed_amount': 'sum',
}).reset_index()
denial_summary.columns = ['denial_reason', 'count', 'amount']
denial_summary = denial_summary.sort_values('count', ascending=False)
denial_summary.to_csv('denial_reason_analysis.csv', index=False)
print("✓ Saved denial_reason_analysis.csv")

# Claims by month
claims['claim_month'] = pd.to_datetime(claims['claim_date']).dt.to_period('M')
monthly_claims = claims.groupby('claim_month').agg({
    'claim_id': 'count',
    'allowed_amount': 'sum',
    'paid_amount': 'sum',
}).reset_index()
monthly_claims.columns = ['month', 'claim_count', 'total_allowed', 'total_paid']
monthly_claims['month'] = monthly_claims['month'].astype(str)
monthly_claims.to_csv('monthly_claims_trend.csv', index=False)
print("✓ Saved monthly_claims_trend.csv")

print("\n" + "="*80)
print("✓ ANALYSIS COMPLETE")
print("="*80 + "\n")
