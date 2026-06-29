#!/usr/bin/env python3
"""
Healthcare Claims Data Generator
Generates realistic healthcare claims data for analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

print("\n" + "="*70)
print("HEALTHCARE CLAIMS DATA GENERATION")
print("="*70 + "\n")

# Define claim statuses and denial reasons
claim_statuses = ['Approved', 'Denied', 'Pending', 'Appealed']
denial_reasons = [
    'Pre-authorization Required',
    'Out of Network',
    'Service Not Covered',
    'Duplicate Claim',
    'Invalid Provider',
    'Procedure Code Mismatch',
    'Patient Not Eligible',
    'Exceeds Benefit Limit',
    'Incomplete Documentation',
    'Age Restriction',
    'Medical Necessity Not Met',
    'Provider Contract Expired',
    'No Denial'
]

# Common procedure codes
procedure_codes = [
    '99213', '99214', '99215',  # Office visits
    '70553', '70554',            # MRI codes
    '71020', '71046',            # X-ray codes
    '92004', '92012',            # Eye exams
    '99203', '99204', '99205'    # Established patient visits
]

# States for geographic distribution
states = ['CA', 'TX', 'NY', 'FL', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI']

print("1. Generating Provider Data...")

# Create provider records
num_providers = 150
providers = {
    'provider_id': range(5001, 5001 + num_providers),
    'provider_name': [f'Medical Center {i}' for i in range(1, num_providers + 1)],
    'provider_type': np.random.choice(['Hospital', 'Clinic', 'Specialist'], num_providers),
    'state': np.random.choice(states, num_providers),
    'network_status': np.random.choice(['In-Network', 'Out-of-Network'], num_providers, p=[0.8, 0.2]),
}

providers_df = pd.DataFrame(providers)
providers_df.to_csv('providers.csv', index=False)
print(f"   ✓ Created {len(providers_df)} provider records")

print("\n2. Generating Member Data...")

# Create member/patient records
num_members = 10000
member_ids = range(1000001, 1000001 + num_members)

members = {
    'member_id': member_ids,
    'member_name': [f'Member_{i}' for i in range(1, num_members + 1)],
    'date_of_birth': [datetime(1950, 1, 1) + timedelta(days=random.randint(0, 20000)) for _ in range(num_members)],
    'gender': np.random.choice(['M', 'F'], num_members),
    'plan_type': np.random.choice(['HMO', 'PPO', 'EPO'], num_members, p=[0.4, 0.4, 0.2]),
    'effective_date': [datetime(2022, 1, 1) + timedelta(days=random.randint(0, 730)) for _ in range(num_members)],
    'state': np.random.choice(states, num_members),
}

members_df = pd.DataFrame(members)
members_df['date_of_birth'] = pd.to_datetime(members_df['date_of_birth'])
members_df['effective_date'] = pd.to_datetime(members_df['effective_date'])
members_df.to_csv('members.csv', index=False)
print(f"   ✓ Created {len(members_df)} member records")

print("\n3. Generating Claims Data...")

# Create claims
num_claims = 50000
claim_ids = range(3001, 3001 + num_claims)

# Generate base claim data
claims_data = {
    'claim_id': claim_ids,
    'member_id': np.random.choice(members_df['member_id'].values, num_claims),
    'provider_id': np.random.choice(providers_df['provider_id'].values, num_claims),
    'claim_date': [datetime(2023, 1, 1) + timedelta(days=random.randint(0, 365)) for _ in range(num_claims)],
    'service_date': [datetime(2023, 1, 1) + timedelta(days=random.randint(0, 365)) for _ in range(num_claims)],
    'procedure_code': np.random.choice(procedure_codes, num_claims),
    'billed_amount': np.random.uniform(100, 5000, num_claims),
}

claims_df = pd.DataFrame(claims_data)
claims_df['claim_date'] = pd.to_datetime(claims_df['claim_date'])
claims_df['service_date'] = pd.to_datetime(claims_df['service_date'])

# Add claim status based on logic
def assign_claim_status(row):
    # Most claims are approved
    if random.random() < 0.75:
        return 'Approved'
    elif random.random() < 0.8:
        return 'Denied'
    else:
        return 'Pending'

claims_df['claim_status'] = claims_df.apply(lambda x: assign_claim_status(x), axis=1)

# Add denial reason
def assign_denial_reason(status):
    if status == 'Denied':
        return np.random.choice(denial_reasons[:-1])  # Exclude 'No Denial'
    else:
        return 'No Denial'

claims_df['denial_reason'] = claims_df['claim_status'].apply(lambda x: assign_denial_reason(x))

# Calculate allowed and paid amounts
claims_df['allowed_amount'] = (claims_df['billed_amount'] * np.random.uniform(0.6, 0.95, num_claims)).round(2)
claims_df['paid_amount'] = claims_df.apply(
    lambda row: row['allowed_amount'] * 0.8 if row['claim_status'] == 'Approved' else 0, axis=1
).round(2)

# Add processing days
claims_df['days_to_process'] = np.random.randint(5, 45, num_claims)

claims_df.to_csv('claims.csv', index=False)
print(f"   ✓ Created {len(claims_df)} claim records")

print("\n4. Generating Line Item Details...")

# Create claim line items (details for each claim)
line_items = []
line_item_id = 8001

for idx, claim in claims_df.iterrows():
    num_lines = random.randint(1, 4)
    
    for _ in range(num_lines):
        line_items.append({
            'line_item_id': line_item_id,
            'claim_id': claim['claim_id'],
            'procedure_code': claim['procedure_code'],
            'units': random.randint(1, 5),
            'unit_price': claim['allowed_amount'] / random.randint(1, 3),
            'line_status': claim['claim_status'],
        })
        line_item_id += 1

line_items_df = pd.DataFrame(line_items)
line_items_df.to_csv('line_items.csv', index=False)
print(f"   ✓ Created {len(line_items_df)} line item records")

print("\n5. Generating Appeals Data...")

# Create appeals for denied claims
denied_claims = claims_df[claims_df['claim_status'] == 'Denied']
appeal_rate = 0.3  # 30% of denied claims get appealed

appeals = []
appeal_id = 2001

for idx, claim in denied_claims.iterrows():
    if random.random() < appeal_rate:
        appeal_status = np.random.choice(['Approved', 'Denied', 'Pending'], p=[0.4, 0.4, 0.2])
        appeals.append({
            'appeal_id': appeal_id,
            'claim_id': claim['claim_id'],
            'appeal_date': claim['claim_date'] + timedelta(days=random.randint(15, 60)),
            'appeal_status': appeal_status,
            'appeal_reason': np.random.choice(['Missing Documentation', 'Medical Necessity', 'Billing Error']),
        })
        appeal_id += 1

appeals_df = pd.DataFrame(appeals)
if len(appeals_df) > 0:
    appeals_df['appeal_date'] = pd.to_datetime(appeals_df['appeal_date'])
    appeals_df.to_csv('appeals.csv', index=False)
    print(f"   ✓ Created {len(appeals_df)} appeal records")
else:
    print("   ✓ No appeal records generated")

print("\n" + "="*70)
print("DATA GENERATION SUMMARY")
print("="*70)
print(f"\nProviders:        {len(providers_df):,} records")
print(f"Members:          {len(members_df):,} records")
print(f"Claims:           {len(claims_df):,} records")
print(f"  - Approved:     {len(claims_df[claims_df['claim_status'] == 'Approved']):,}")
print(f"  - Denied:       {len(claims_df[claims_df['claim_status'] == 'Denied']):,}")
print(f"  - Pending:      {len(claims_df[claims_df['claim_status'] == 'Pending']):,}")
print(f"Line Items:       {len(line_items_df):,} records")
print(f"Appeals:          {len(appeals_df):,} records")
print(f"\nTotal Amount:     ${claims_df['billed_amount'].sum():,.2f}")
print(f"Total Paid:       ${claims_df['paid_amount'].sum():,.2f}")
print(f"Approval Rate:    {len(claims_df[claims_df['claim_status'] == 'Approved']) / len(claims_df) * 100:.1f}%")

print("\n✓ All CSV files created successfully!")
print("="*70 + "\n")
